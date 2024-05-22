import os
import re
import pandas as pd
import numpy as np
from openai import OpenAI
import os
import json
import tiktoken
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from src.articles._utils import truncate_text_to_token_limit


class TrainingDataGenerationService:

    def __init__(self, shortlisted_articles_df, folder_path, model='gpt-4'):
        self.model = model
        self.folder_path = folder_path
        self.system_prompt = TrainingDataGenerationService.set_system_prompt()
        self.shortlisted_articles_df = shortlisted_articles_df
        self.client = OpenAI(api_key=os.environ['OPENAI_KEY'])
        self.encoder = tiktoken.encoding_for_model(model)
        self.system_tokens = len(self.encoder.encode(self.system_prompt))
        self.output_tokens = 1024
        self.total_tokens = 3584
        self.content_tokens = min(self.total_tokens - self.system_tokens - self.output_tokens, 1536)
        self.valid_response_dict = {}
        self.invalid_response_dict = {}
        self.file_path = f"{self.folder_path}/{self.model}-responses-{datetime.now().strftime('%Y-%b-%d')}.csv"
        self.ignore_fetched_articles()

    def ignore_fetched_articles(self):
        if os.path.exists(self.file_path):
            fetched_articles_df = pd.read_csv(self.file_path, header=None)
            fetched_articles = list(fetched_articles_df[1].unique())
            self.shortlisted_articles_df = self.shortlisted_articles_df[~self.shortlisted_articles_df['article_id'].isin(fetched_articles)]

    @staticmethod
    def set_system_prompt():
        prompt = '''You are an expert chief editor for a leading Indian business and financial content website. You evaluate critical attributes of articles to gatekeep content quality. The following are 19 attributes with the format of attribute (datatype): <instruction>
        '{"summary": "<Summarize the article, focusing on: a. Thoroughness: Include essential details and expand on headline points. b. Readability: Ensure proper grammar, 2-3 points, up to 80 words. c. Faithfulness: Don\'t mention any details which are not part of the article. d. Accuracy: Verify numbers, dates, and events. f. Structure: Single-line points preceded by relevant emoji and label. g. Format: Use !emoji! label: point format without preamble/postamble, adhering to a 3-point maximum. We will call this format as _summary_markdown_format_ -> \'!emoji1! label1: point1 \\n !emoji2! label2: point2. The platform is visited by users of all age groups and hence do not use any inappropriate content or emojis>", "summary_critique": "<Evaluate the summary against the article for thoroughness, readability, faithfulness, accuracy, and the _summary_markdown_format_, noting any missed details or format issues. Emoji should be in unicode format>", "improved_summary": "<Improve the summary using feedback from the critique, following the _summary_markdown_format_>", "top_queries": "<List 5 relevant keywords/queries, separated by semicolons, without quotes to ensure JSON compatibility. keywords are short 1-2 words, while queries last from 3-6 words>", "indian_or_international": "<Specify if the article is \'indian\' or \'international\'>", "business_or_financial_article": "<True or False, based on the article\'s relevance to Indian corporations, investors, and policies impacting them>", "relevant_for_indians": "<True or False, considering the article\'s applicability to Indian readers. Most international news are not relevant for Indians, except if they are of very popular entities (like google, openai, Microsoft) or have global impact like fed changes>", "category": "<categorize the article into one of the 5 distinct categories based on the primary focus of article. a. irrelevant: if business_or_financial_article is False  b. financial: information of markets, financial instruments or company financial reports. c. business: information of operational, strategic, leadership or other non financial news of companies. d. economic_policy: information of economic trends or policy and regulatory impacts on larger industry. e. personal_finance: provides guidance on individual financial management, such as investment for personal goals, savings, taxation, budget updates, insurance or other financial products, directly targeting individual consumers and passive investors>", "article_interest_duration_evaluation": "<Analyze for how many days the information in the article will of interest to users after it is published>", "article_interest_duration": "<Determine the article\'s interest duration from options: 1, 3, 7, 14, 30, -1 (timeless), based on the evaluation>", "popularity_evaluation": "<Assess the article\'s potential popularity. Score each of reader_interest, headline_effectiveness, event_novelty, and emotional_impact between 0 to 1. Be conservative with scores over 0.4>", "popularity_evaluation_critique": "<Critique the popularity assessment for possible overestimations or underestimations>", "final_reader_interest_score": "<0 to 1 float>", "final_headline_effectiveness_score": "<0 to 1 float>", "final_event_novelty_score": "<0 to 1 float>", "final_emotional_impact_score": "<0 to 1 float>", "improved_headline": "<Craft an engaging headline that captures the article\'s essence without resorting to clickbait>", "article_type": "<Identify the article as fact, opinion, analysis, educational, or sponsored, based on its content and presentation>", "article_sentiment": "<Determine if the article\'s sentiment is bullish, bearish, or NA (neutral)>"}'
        your response should be a json structure with all the 19 above keys without missing any key. It is very important that the response is directly readable with json.loads(). no preamble or postamble.'''
        return prompt

    def parse_gpt_api_response(self, article_id, user_prompt, api_response):
        model = api_response.model
        prompt_tokens = api_response.usage.prompt_tokens
        completion_tokens = api_response.usage.completion_tokens
        json_generated = False
        raw_response = api_response.choices[0].message.content
        try:
            model_response = json.loads(raw_response.strip())
            json_generated = True
        except:
            model_response = raw_response
        # Build the dictionary with the required information
        extracted_data = {
            'article_id': article_id,
            'system_prompt': self.system_prompt,
            'user_prompt': user_prompt,
            'model': model,
            'model_response': json.dumps(model_response),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'proper_json_generated': json_generated
        }

        return json_generated, extracted_data

    def fetch_save_attributes(self, article_row):
        truncated_content = truncate_text_to_token_limit(text=article_row.full_content, encoder=self.encoder, token_limit=self.content_tokens)
        res_gpt = self.client.chat.completions.create(model=self.model, messages=[{'role': 'system', 'content': self.system_prompt.replace('\n', ' ')},
                                                                                  {'role': 'user', 'content': f'{truncated_content}|article_end|'}])
        valid_json, parsed_res = self.parse_gpt_api_response(article_id=article_row.article_id, user_prompt=truncated_content, api_response=res_gpt)
        if valid_json:
            self.valid_response_dict[article_row.article_id] = parsed_res
            self.save_attributes(response_json=parsed_res)
            return True
        else:
            self.invalid_response_dict[article_row.article_id] = parsed_res
            return False

    def save_attributes(self, response_json):
        cur_df = pd.DataFrame(response_json, index=['i', ])
        cur_df.to_csv(self.file_path, header=None, mode='a')

    def get_gpt4_attributes_for_article_ids(self, fraction=1):
        start_time = time.time()
        valid_responses = 0
        invalid_responses = 0
        shortlisted_rows = self.shortlisted_articles_df.sample(frac=fraction)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.fetch_save_attributes, article_row) for article_row in shortlisted_rows.itertuples()]
            for future in as_completed(futures):
                fetched = future.result()
                if fetched:  # Timeout or other errors
                    valid_responses += 1
                    if valid_responses % 50 == 0:
                        print(f'completed {valid_responses} in {time.time() - start_time} seconds')
                else:
                    invalid_responses += 1
                    if invalid_responses % 20 == 0:
                        print(f'now {invalid_responses} invalid responses')
        print(f'done in {time.time() - start_time} seconds')
        return valid_responses

    def fix_json_for_invalid_response(self, article_id):
        cur_dict = self.invalid_response_dict[article_id]
        improved_api_response = self.client.chat.completions.create(model=self.model, messages=[
            {'role': 'system', 'content': 'fix the following json to be readable using json.loads(). simply out the new json. no preamble and no postamble'},
            {'role': 'user', 'content': cur_dict['model_response']}])
        raw_response = improved_api_response.choices[0].message.content
        prompt_tokens = cur_dict['prompt_tokens'] + improved_api_response.usage.prompt_tokens
        completion_tokens = cur_dict['completion_tokens'] + improved_api_response.usage.completion_tokens
        json_generated = False
        try:
            model_response = json.loads(raw_response)
            json_generated = True
        except:
            model_response = raw_response
            print(f'json not properly generated for {article_id} at {"{:%b %d, %Y %H:%M}".format(datetime.now())}')
        extracted_data = {
            'article_id': article_id,
            'system_prompt': self.system_prompt,
            'user_prompt': cur_dict['user_prompt'],
            'model': cur_dict['model'],
            'model_response': json.dumps(model_response),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'proper_json_generated': json_generated
        }
        return json_generated, extracted_data

    def fix_json_for_all_invalid_responses(self):
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.fix_json_for_invalid_response, article_id) for article_id in list(self.invalid_response_dict.keys())]
            for future in as_completed(futures):
                json_generated, parsed_response = future.result()
                if json_generated:
                    self.save_attributes(response_json=parsed_response)
                    self.invalid_response_dict.pop(parsed_response['article_id'])


