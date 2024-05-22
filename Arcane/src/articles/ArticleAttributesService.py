from datetime import datetime

import numpy as np
import pandas as pd
import requests
import json
import os
import re
import uuid
import logging

from sql.articles.MongoDBArticle import MongoDBArticle
from sql.candidates.CandidateSQL import CandidateSQL
from src.candidates._utils import get_prior_for_popularity, is_candidate
from constants import BACKEND_URL, YT_SOURCE_ID
from sql.articles.ArticleAttributesSQL import ArticleAttributesSQL
from src.articles.prompt import system_prompt
from transformers import AutoTokenizer
import boto3
from botocore.config import Config
from src.articles._utils import truncate_text_to_token_limit
from src.articles.ArticleService import ArticleService
from src.data_models.Article import Article
from src.articles.SummaryService import SummaryService
from src.llm_finetuning.ResponseCleanerService import ResponseCleanerService

logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)

ch = logging.StreamHandler()
ch.setLevel(level)

# add ch to logger
logger.addHandler(ch)

llm_finetune_id = 'OpenHermes_WatermelonUvulaMarigold'


class ArticleAttributesService:
    # TODO: - update is_fin and india relevance flags in mongo



    def __init__(self):
        self.tokenizer = AutoTokenizer.from_pretrained('teknium/OpenHermes-2.5-Mistral-7B', use_fast=True)
        self.output_token_limit = 1024
        self.content_token_limit = self.get_content_token_limit()
        self.llm_endpoint = os.environ.get('LLM_SAGEMAKER_ENDPOINT')

    def get_content_token_limit(self):
        message_template = [{"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"{''}\n"}]
        instruction_tokens = len(self.tokenizer.apply_chat_template(message_template, add_generation_prompt=True))
        buffer_tokens = 10
        return 3584 - self.output_token_limit - instruction_tokens - buffer_tokens

    @staticmethod
    def get_article(article_id) -> Article:
        def convert_key_to_snake(k):
            return re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()

        if os.environ.get('DEBUG'):
            article_json = ArticleService.get_Article(article_id=article_id)
            keys = list(article_json.keys())
            for k in keys:
                article_json[convert_key_to_snake(k)] = article_json[k]
            return Article.from_dict(article_json)
        else:
            return ArticleService.get_Article(article_id=article_id)

    def generate_response_from_fine_tuned_llm(self, prompt, article_id, sagemaker_runtime):
        llm_request_id = uuid.uuid4()
        params = {
            "do_sample": True,
            "top_p": 0.95,
            "temperature": 0.5,
            "max_new_tokens": self.output_token_limit,
            "repetition_penalty": 1.02,
            "stop": ["###", "</s>", self.tokenizer.eos_token],
            "return_full_text": False
        }
        request = {"inputs": prompt, "parameters": params, "stream": False}
        # request['parameters']['adapter_id'] = 'lorax/OpenHermes-2.5-Adapter-Attributes-WatermelonUvulaMarigold'
        # request['parameters']['adapter_source'] = 's3'
        logger.info(f'llm request raised for {article_id}')
        # region = "ap-south-1"  # replace with your preferred region
        # config = Config(
        #     read_timeout=80,
        #     retries={
        #         'max_attempts': 0
        #     }
        # )
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=self.llm_endpoint,
            Body=json.dumps(request),
            ContentType="application/json",
        )
        logger.info(f'llm response received for {article_id}')
        response_body = response['Body'].read()
        try:
            llm_request = {'request_id': str(llm_request_id), 'article_id': article_id, 'params': params,
                           'endpoint': self.llm_endpoint, 'model_finetune_id': llm_finetune_id,
                           'prompt': prompt, 'response': json.loads(response_body)}
            MongoDBArticle.save_llm_response_to_collection(document=llm_request)
            logger.info(f'saved the llm response for {article_id} to mongo')
        except:
            logger.info(f'error converting the response body to json and saving to mongo')
        return response_body

    @staticmethod
    def save_summary_to_mongo(article_id, article_summary, article_title, finetune_id):
        url = f'{BACKEND_URL}/cloud/articles/{article_id}/ai-generated-info'
        data = {'model': finetune_id, 'summary': {'value': article_summary, 'additionalInfo': {}},
                'title': {'value': article_title, 'additionalInfo': {}}}
        r = requests.put(url, json=data)
        return r

    @staticmethod
    def default_attributes_for_podcast():
        default_values = {
            "summary": "",
            "summary_critique": "",
            "improved_summary": "",
            "top_categories": "",
            "financial_or_business_news": True,
            "indian_or_international": "indian",
            "relevant_for_india": True,
            "article_validity_duration_evaluation": "",
            "article_validity_duration": -1,
            "popularity_evaluation": "",
            "popularity_evaluation_critique": "",
            "final_reader_interest_score": 0.5,
            "final_headline_effectiveness_score": 0.5,
            "final_event_novelty_score": 0.5,
            "final_emotional_impact_score": 0.5,
            "popularity": "moderately_popular",
            "improved_headline": "",
            "article_type": "opinion",
            "article_sentiment": "na"
        }
        return default_values

    def compute_save_article_attributes_from_llm(self, article_id, retry_count=0, max_retries=2):

        article = ArticleService.get_Article(article_id=article_id)
        # flow for podcasts
        if article.content_type == 'PODCAST_EPISODE':
            default_values = ArticleAttributesService.default_attributes_for_podcast()
            ArticleAttributesSQL.save_article_attributes(article_id=article_id, article_attributes=default_values, finetune_id='podcast_default_values')
            ArticleAttributesService.update_candidates_with_article(article=article, article_attributes=default_values)
            return default_values

        if article.source_id == YT_SOURCE_ID:
            return {}

        # flow for articles
        request_id = uuid.uuid4()
        article_attributes = {}
        my_config = Config(
            region_name='ap-south-1',
            retries={
                'max_attempts': 5,
                'mode': 'standard'
            },
            max_pool_connections=40  # Increase the pool size
        )

        # Create a SageMaker Runtime client with the custom configuration
        sess1 = boto3.session.Session()
        sagemaker_runtime = sess1.client("sagemaker-runtime", config=my_config)

        def retry():
            if retry_count <= max_retries:
                return self.compute_save_article_attributes_from_llm(article_id, retry_count + 1)
            else:
                # If max retries to llm server are done without any luck, then try gpt4
                logger.info(f'{max_retries} max retries exhausted for getting attributes from llm server for {article_id}')
                return self.get_article_attributes_from_gpt4(prompt=prompt, article_id=article_id)

        logger.info(f'attempt {retry_count} for getting attributes from fine tuned llm for {article_id}. request id {request_id}')
        article_content = article.full_content
        prompt = self.generate_prompt(article_content=article_content)
        response_body = self.generate_response_from_fine_tuned_llm(prompt=prompt, article_id=article_id, sagemaker_runtime=sagemaker_runtime)
        # TODO: - write prompt and response to mongo db
        logger.info(f'response received as {response_body}')

        try:
            parsed_response = json.loads(response_body)[0]['generated_text']
            if isinstance(json.loads(parsed_response), dict):
                article_attributes = json.loads(parsed_response)
            else:
                article_attributes = json.loads(json.loads(parsed_response))
        except Exception as e:
            logger.error(f'received error of {e} while loading and parsing response body as json and get generated_text for {article_id}: {response_body}')
            return response_body
            # If the response is not parsable then call again
        article_attributes = self.get_cleaned_attributes_json(article_attributes=article_attributes)
        if article_attributes:
            article_attributes['popularity'] = ArticleAttributesService.derive_popularity(article_attributes)
            ArticleAttributesService.save_llm_article_attributes(article_id=article_id, article_attributes=article_attributes)
            logger.info(f'article attributes for {article_id} saved to db')
            ArticleAttributesService.update_candidates_with_article(article=article, article_attributes=article_attributes)
            return article_attributes
        else:
            retry_attributes = retry()
            article_attributes.update(retry_attributes)
        return article_attributes

    @staticmethod
    def derive_popularity(article_attributes):
        total_sum = article_attributes['final_reader_interest_score'] + article_attributes['final_headline_effectiveness_score'] + article_attributes['final_event_novelty_score'] + article_attributes['final_emotional_impact_score']
        if total_sum < 1.5:
            return 'niche'
        elif total_sum < 2.5:
            return 'moderately_popular'
        else:
            return 'breaking_news'

    # TODO: - add functionality to update candidates if article is already in it
    @staticmethod
    def save_llm_article_attributes(article_id, article_attributes):
        if article_attributes:
            ArticleAttributesSQL.save_article_attributes(article_id=article_id, article_attributes=article_attributes, finetune_id=llm_finetune_id)
            ArticleAttributesService.save_summary_to_mongo(article_id=article_id,
                                                           article_summary=article_attributes['improved_summary'],
                                                           article_title=article_attributes['improved_headline'],
                                                           finetune_id=llm_finetune_id)
            # TODO: - currently article isn't removed from candidates based on the attributes. TBD later

    @staticmethod
    def update_candidates_with_article(article: Article, article_attributes):
        # If article is part of the candidates, its external prior is updated based on the attributes
        published_time = pd.to_datetime(article.published_time).replace(tzinfo=None)
        hours_since_publication = (datetime.today() - published_time) / np.timedelta64(1, 'h')
        article_attributes['hours_since_publication'] = hours_since_publication
        article_attributes['financial_news'] = article_attributes['financial_or_business_news']
        article_attributes['validity_in_hours'] = article_attributes['article_validity_duration'] * 24
        add_to_candidates = is_candidate(attributes_dict=article_attributes)
        if article.source_id == YT_SOURCE_ID:
            add_to_candidates = False
        if add_to_candidates:
            # TODO:- rename the popularity scores to simpler names here itself
            prior_a = get_prior_for_popularity(article_attributes)
            CandidateSQL.add_article_to_candidates_with_priors(article_id=article.article_id, published_at=article.published_time,
                                                               source_id=article.source_id, prior_a=prior_a, prior_b=10, content_type=article.content_type)
            logger.info(f'{article.article_id} added to candidates')
        else:
            CandidateSQL.remove_article_from_candidates(article_id=article.article_id)
            logger.info(f'{article.article_id} removed from candidates')

    @staticmethod
    def correct_validity_duration(val):
        try:
            val = int(val)
        except:  # if it can't be cast to int
            return None

        valid_days = sorted([-1, 1, 3, 7, 14, 30])[::-1]  # sort in descending order
        # duration is a string value of a valid duration
        if val in valid_days:
            return val
        # duration is a number or string value of an invalid duration
        for i in valid_days:
            if val > i:
                return i  # return the largest duration less than value
        return -1  # it means val is < -1

    @staticmethod
    def clean_attributes_json(attributes):
        attributes['category'] = ResponseCleanerService.fix_category(attributes['category'])
        attributes['financial_or_business_news'] = ResponseCleanerService.fix_bool_flag(attributes['business_or_financial_article'])
        attributes['relevant_for_india'] = ResponseCleanerService.fix_bool_flag(attributes['relevant_for_indians'])
        attributes['article_sentiment'] = ResponseCleanerService.fix_article_sentiment(attributes['article_sentiment'])
        attributes['article_type'] = ResponseCleanerService.fix_article_type(attributes['article_type'])
        attributes['article_validity_duration'] = ResponseCleanerService.fix_validity_duration(attributes['article_interest_duration'])
        return attributes

    def get_cleaned_attributes_json(self, article_attributes):
        if not self.validate_attributes_keys(article_attributes):
            return {}
        article_attributes = ArticleAttributesService.clean_attributes_json(attributes=article_attributes)

        if not self.validate_attributes_values(article_attributes):
            return {}
        # summary validation
        if not ResponseCleanerService.validate_summary_emojis(article_attributes['improved_summary']):
            return {}
        # convert markdown summary to html summary
        # article_attributes['improved_summary'] = SummaryService.convert_markdown_to_html(article_attributes['improved_summary'])
        article_attributes['improved_summary'] = json.dumps(ResponseCleanerService.convert_summary_to_dicts(article_attributes['improved_summary']))
        # cleaning popularity flag
        for popularity_attribute in ['final_reader_interest_score', 'final_headline_effectiveness_score', 'final_event_novelty_score', 'final_emotional_impact_score']:
            article_attributes[popularity_attribute] = ArticleAttributesService.clean_popularity_score_attribute(attribute=popularity_attribute,
                                                                                                                 score=article_attributes[popularity_attribute])
        return article_attributes

    @staticmethod
    def get_article_attributes_from_gpt4(prompt, article_id):
        request_id = uuid.uuid4()
        logger.info(f'calling gpt4 for article_id {article_id} with prompt {prompt}')
        # TODO: - write prompt and response to mongo db
        return {}

    def generate_prompt(self, article_content):
        truncated_content = truncate_text_to_token_limit(text=article_content, encoder=self.tokenizer, token_limit=self.content_token_limit)
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"|article_start|\n {truncated_content}\n|article_end|\n"}]
        context_prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        context_prompt = re.sub(r'\n+', '\n', context_prompt)
        return context_prompt

    @staticmethod
    def validate_attributes_keys(attributes):
        expected_dict_structure = {
            "summary": "",
            "summary_critique": "",
            "improved_summary": "",
            "top_queries": "",
            "business_or_financial_article": "",
            "indian_or_international": "",
            "relevant_for_indians": "",
            "category": "",
            "article_interest_duration_evaluation": "",
            "article_interest_duration": "",
            "popularity_evaluation": "",
            "popularity_evaluation_critique": "",
            "final_reader_interest_score": "",
            "final_headline_effectiveness_score": "",
            "final_event_novelty_score": "",
            "final_emotional_impact_score": "",
            "improved_headline": "",
            "article_type": "",
            "article_sentiment": ""
        }
        return sorted(list(expected_dict_structure.keys())) == sorted(list(attributes.keys()))

    @staticmethod
    def validate_attributes_values(attributes):
        valid_fin_flag = isinstance(attributes['financial_or_business_news'], bool)
        valid_india_flag = isinstance(attributes['relevant_for_india'], bool)
        valid_duration = attributes['article_validity_duration'] in [-1, 1, 3, 7, 14, 30]
        valid_category = attributes['category'] in ['business', 'economic_policy', 'financial', 'irrelevant', 'personal_finance']
        return valid_fin_flag and valid_india_flag and valid_duration and valid_category

    @staticmethod
    def clean_popularity_score_attribute(attribute, score):
        default_values = {'final_reader_interest_score': 0.33, 'final_headline_effectiveness_score': 0.5,
                          'final_event_novelty_score': 0.25, 'final_emotional_impact_score': 0.33}
        assert attribute in list(default_values.keys())
        if not isinstance(score, float):
            try:
                score = float(score)
            except:
                return default_values[attribute]
        if not 0 < score < 1:
            return default_values[attribute]
        return score

    @staticmethod
    def validated_summary(article, summary):
        if len(summary) < 15 or len(summary.split(' ')) < 5 or len(summary) > 1000:
            return ''
        return summary
