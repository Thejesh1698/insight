import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests
import json
import os
import re
import uuid
import logging

from anthropic import Anthropic
from transformers import AutoTokenizer
import boto3
from botocore.config import Config
from openai import OpenAI
# logger = logging.getLogger('__name__')
logger = logging.getLogger()
level = logging.CRITICAL
logger.setLevel(level)

ch = logging.StreamHandler()
ch.setLevel(level)

# add ch to logger
logger.addHandler(ch)

llm_finetune_id = 'OpenHermes_ApricotTangerineScallop'
model_id = "teknium/OpenHermes-2.5-Mistral-7B"
tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))
anthropic_client = Anthropic(api_key=os.environ.get('ANTHROPIC_KEY'))


class QueryService:

    @staticmethod
    def format_prompt(query_text, query_date=None):
        """
        :param query_text: search query text
        :param query_date: can be null. if provided, should be of the format '%d/%m/%y'
        :return:
        """
        if not query_date:
            query_date = datetime.now().strftime('%d/%m/%y')
        system_prompt = f'''
        You are an expert in taking user queries on an indian financial and business website and extracting certain attributes like below. You generate the attributes in a csv safe format with columns separated by comma. The final attribute of web search query is extremely important, and should directly result in relevant results when the query has any financial or business connection. If the entity or query is too vague to get only financial or business results, then append it with ‘financial and business news’. Today is {query_date}. When using in web query, then use %d/%m/%y
        - is_fin_business_query, recency_importance (High for very volatile, medium for slowly changing stuff like regulations or industry related, and low for very less changing like educational and guides), vague (too vague to generate financial or business results), web_search_query (ideal web search query which will result in most relevant financial results if applicable)
        Generate the responses for the below user query. No preamble or postamble.
        '''
        modified_query_text = f'{query_text}  in {datetime.now().strftime("%Y")}'
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"|query_start|\n'{modified_query_text}'\n|query_end|'\n"}]
        context_prompt = tokenizer.decode(tokenizer.apply_chat_template(messages, add_generation_prompt=True))
        prompt = re.sub(r'\n+', '\n', context_prompt)
        return prompt

    @staticmethod
    def format_prompt_for_openai(query_text, query_date=None):
        if not query_date:
            query_date = datetime.now().strftime('%d/%m/%y')
        openai_system_prompt = f'''You are an expert in taking user queries on an indian financial and business website and extracting important attributes separated by comma. The final attribute of web search query is extremely important, and should directly result in relevant results when the query has any financial or business connection. If the entity or query is too vague to get only financial or business results, then append it with ‘financial and business news’. Today is {query_date}. When using in web query, then use %d/%m/%y
- is_fin_business_query(True/False), recency_importance (High for very volatile, medium for slowly changing stuff like regulations or industry related, and low for very less changing like educational and guides), vague(True/False), web_search_query
example query: best credit cards. example output: True,Medium,False,best credit cards 2024 reviews. Generate the responses for the below user query. No preamble or postamble.'''
        openai_system_prompt = re.sub(r'\n+', '\n', openai_system_prompt)
        return openai_system_prompt

    @staticmethod
    def understand_query_using_openai(query_text, query_date=None):
        model = 'claude-3-haiku-20240307'
        system_prompt = QueryService.format_prompt_for_openai(query_text=query_text,query_date=query_date)
        # api_response = client.chat.completions.create(model=model, messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': query_text}], stream=False)
        # model = api_response.model
        # prompt_tokens = api_response.usage.prompt_tokens
        # completion_tokens = api_response.usage.completion_tokens
        # evaluation = api_response.choices[0].message.content
        api_response = anthropic_client.messages.create(model=model, max_tokens=768, messages=[{'role': 'user', 'content': f'{system_prompt}. query: {query_text}'}])
        model = api_response.model
        prompt_tokens = api_response.usage.input_tokens
        completion_tokens = api_response.usage.output_tokens
        evaluation = api_response.content[0].text
        is_fin, recency_weight, improved_query = QueryService.parse_query_llm_response(query_text, evaluation)
        if improved_query:
            improved_query = QueryService.convert_to_readable_date_in_query(improved_query)
        query_understanding_info = {'model': model, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'system_prompt': system_prompt, 'user_prompt': query_text, 'evaluation': evaluation}
        return is_fin, recency_weight, improved_query, query_understanding_info

    @staticmethod
    def understand_query_using_llm(query_text, query_date=None):
        sess = boto3.session.Session()
        my_config = Config(
            region_name='ap-south-1',
            retries={
                'max_attempts': 5,
                'mode': 'standard'
            },
            max_pool_connections=10  # Increase the pool size
        )
        smr = sess.client("sagemaker-runtime", config=my_config)

        prompt = QueryService.format_prompt(query_text, query_date=query_date)
        parameters = {
            "do_sample": True,
            "top_p": 0.9,
            "temperature": 0.5,
            "max_new_tokens": 364,
            "repetition_penalty": 1.02,
            "stop": ["###", "</s>", tokenizer.eos_token],
        }
        request = {"inputs": prompt, "parameters": parameters, "stream": False}
        llm_call_time = time.time()
        k = smr.invoke_endpoint(
            EndpointName=f"OpenHermes-search-query-KiwiHammockEscalator",
            Body=json.dumps(request),
            ContentType="application/json",
        )
        # logger.info(f'query understanding llm in {time.time() - llm_call_time} seconds')
        resp = k['Body'].read()
        evaluation = json.loads(resp)[0]['generated_text']
        # TODO: - save this to mongo
        is_fin, recency_weight, improved_query = QueryService.parse_query_llm_response(query_text, evaluation)
        if improved_query:
            improved_query = QueryService.convert_to_readable_date_in_query(improved_query)
        return is_fin, recency_weight, improved_query

    @staticmethod
    def convert_to_readable_date_in_query(input_string):
        # Function to convert each matched date to the desired format
        def convert_match(match):
            # Extract day, month, and year from the match
            day, month, year = match.groups()
            # Parse the date using datetime.strptime and then format it into "%d %B %Y"
            formatted_date = datetime.strptime(f"{day}/{month}/20{year}", "%d/%m/%Y").strftime("%d %B %Y")
            return formatted_date
        # Define the pattern for dates in the format %d/%m/%y
        date_pattern = r"\b(\d{2})/(\d{2})/(\d{2})\b"
        # Use re.sub() with the convert_match function to replace all occurrences
        replaced_string = re.sub(date_pattern, convert_match, input_string)
        return replaced_string

    @staticmethod
    def parse_query_llm_response(query, evaluation):
        values = evaluation.split(',')
        if len(values) == 4:
            is_fin_query, recency_imp, vague, alternate_query = values
            if is_fin_query.lower() == 'true':
                if recency_imp.lower() not in ['high', 'medium', 'low']:
                    recency_imp = 'medium'
                else:
                    recency_imp = recency_imp.lower()
                # the alternate query shouldn't be too long
                if len(alternate_query) > max(50, 2 * len(query)):
                    alternate_query = query
                return True, recency_imp, alternate_query
            else:
                return False, None, None
        else:
            return True, None, None
