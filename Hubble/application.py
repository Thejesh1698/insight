import os
import xml.etree.ElementTree as ET
from datetime import datetime

import numpy as np
from anthropic import Anthropic
tree = ET.parse('./conf/application.run.xml')
root = tree.getroot()
envs_element = root.find('./configuration/envs')
for variable in envs_element.findall('env'):
    name = variable.get('name')
    value = variable.get('value')
    os.environ[name] = value
import threading
import time
from src.FunctionCallingService import FunctionCallingService
from flask import Flask, jsonify, request, Response, stream_with_context
from sql.MongoDatabaseConnection import MongoDatabaseConnection
from src.BingWebSearch import BingWebSearch
from src.EmbeddingsService import EmbeddingsService
from src.HybridSearchService import HybridSearchService
from src.QueryService import QueryService
from src._utils import clean_search_query
import logging
from openai import OpenAI
from botocore.config import Config
import io
from src.SummaryService import SummaryService
from time import sleep
application = Flask(__name__)
import boto3
import json


mongo_conn = MongoDatabaseConnection()
logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)

ch = logging.StreamHandler()
ch.setLevel(level)

# add ch to logger
logger.addHandler(ch)
embedding_service = EmbeddingsService(hf_model_path='BAAI/bge-large-en-v1.5')
sqs = boto3.client('sqs', aws_access_key_id=os.environ.get('AWS_ACCESS_KEY'), aws_secret_access_key=os.environ.get('AWS_SECRET_KEY'), region_name='ap-south-1')
summary_queue_url = 'https://sqs.ap-south-1.amazonaws.com/005418323977/search-ai-generated-summary'
ES_URL = f'https://{os.environ.get("ES_HOST")}/finance-content/_search'

openai_client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))
anthropic_client = Anthropic(api_key=os.environ.get('ANTHROPIC_KEY'))


class TokenIterator:
    def __init__(self, stream):
        self.byte_iterator = iter(stream)
        self.buffer = io.BytesIO()
        self.read_pos = 0

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            self.buffer.seek(self.read_pos)
            line = self.buffer.readline()
            if line and line[-1] == ord("\n"):
                self.read_pos += len(line) + 1
                full_line = line[:-1].decode("utf-8")
                line_data = json.loads(full_line.lstrip("data:").rstrip("/n"))
                return line_data["token"]["text"]
            chunk = next(self.byte_iterator)
            self.buffer.seek(0, io.SEEK_END)
            self.buffer.write(chunk["PayloadPart"]["Bytes"])


@application.route('/search_query_web', methods=['POST'])
def search_for_query_web():
    start_time = time.time()
    data = request.get_json()
    query_text = data['query_text']
    logger.info(f'received request for query {query_text}')
    query_text = clean_search_query(query_text)
    if not query_text:
        return {
            'searchArticleIds': [],
            'additionalInfo': {}
        }
    is_fin, recency_weight, improved_query, query_info = QueryService.understand_query_using_openai(query_text=query_text)
    print(is_fin, recency_weight, improved_query)
    logger.info(f'query understanding for {query_text} done in {time.time() - start_time} secs')
    if not is_fin:
        return {
            'searchArticleIds': [],
            'additionalInfo': {'query_understanding': query_info}
        }
    search_response_object = BingWebSearch.perform_bing_web_search(query_text=query_text, recency_importance=recency_weight)
    # search_response_object = HybridSearchService.perform_hybrid_reranked_search(query_text=query_text, recency_importance=recency_weight)
    search_response_object['additionalInfo']['query_understanding'] = query_info
    return search_response_object


@application.route('/search_query_portfolio', methods=['POST'])
def search_for_query_portfolio():
    start_time = time.time()
    data = request.get_json()
    query_text = data['query_text']
    user_id = data['userId']
    logger.info(f'received request for query {query_text} from user {user_id}')
    query_text = clean_search_query(query_text)
    if not query_text or not user_id:
        return {
            'searchArticleIds': [],
            'additionalInfo': {}
        }
    user_id = int(user_id)
    search_response_object = FunctionCallingService.parse_details_from_gpt(query=query_text, user_id=user_id)
    return search_response_object


@application.route('/search_query', methods=['POST'])
def search_for_query():
    data = request.get_json()
    query_text = data['query_text']
    print(f'query text is {query_text}')
    query_text = clean_search_query(query_text)
    if not query_text:
        return {
            'searchArticleIds': [],
            'additionalInfo': {}
        }
    is_fin, recency_weight, improved_query, query_info = QueryService.understand_query_using_openai(query_text=query_text)
    print(is_fin, recency_weight, improved_query)

    if not is_fin:
        return {
            'searchArticleIds': [],
            'additionalInfo': {'query_understanding': query_info}
        }
    if improved_query:
        search_response_object = HybridSearchService.perform_hybrid_reranked_search(query_text=query_text, recency_importance=recency_weight)
    else:
        search_response_object = HybridSearchService.perform_hybrid_reranked_search(query_text=query_text, recency_importance=recency_weight)
    search_response_object['additionalInfo']['query_understanding'] = query_info
    return search_response_object


@application.route('/summarize_search', methods=['GET'])
def summarize_search_results():
    streamed_summary = []
    summary_streamed_from_llm = False
    llm_name = 'OpenHermes-Search-PinkSparrowOnTV'
    my_config = Config(
        region_name='ap-south-1',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        },
        max_pool_connections=40  # Increase the pool size
    )

    # Create a SageMaker Runtime client with the custom configuration
    sess1 = boto3.session.Session()
    sagemaker_runtime = sess1.client("sagemaker-runtime", config=my_config)

    def stream_sagemaker(rqst):
        nonlocal streamed_summary, summary_streamed_from_llm
        # if 'web_sources' in rqst:
        #     web_sources = rqst.pop('web_sources')
        #     logger.info(f'web search sources are {web_sources}')
        response = sagemaker_runtime.invoke_endpoint_with_response_stream(
            EndpointName='OpenHermes-Search-PinkSparrowOnTV',
            Body=json.dumps(rqst),
            ContentType="application/json",
        )
        for token in TokenIterator(response["Body"]):
            streamed_token = token if token != "\n" else "<br>"
            streamed_summary.append(streamed_token)
            yield streamed_token
        summary_streamed_from_llm = True

    def stream_error(query):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        message = f'''I am sorry, but I am unable to assist you with your query of {query}.<br>As a financial assistant AI developed by the **Insight** team, my expertise is tailored specifically to address inquiries related to Indian finance. Please feel free to ask me any questions within this domain, and I'll do my best to provide you with the information you need 🚀.'''
        streamed_summary = [message]
        llm_name = ''
        for word in message.split(" "):  # Splitting the message into words
            sleep(0.01)
            yield f"{word} "
        summary_streamed_from_llm = True

    def handle_post_streaming():
        complete_response = ''.join(streamed_summary)
        if search_id:
            response_object = {'search_id': search_id, 'summary_info': {'streamed_summary': complete_response,
                                                                        'llm_name': llm_name}}
            logger.info(f'will be logging {response_object} for search_id {search_id}')
            sqs_response = sqs.send_message(QueueUrl=summary_queue_url, MessageBody=json.dumps(response_object))
            logger.info(f'response from sqs for {search_id} is {sqs_response}')

    def background_task_with_dynamic_wait():
        max_wait_time = 30  # Maximum time to wait in seconds
        start_time = time.time()
        while not summary_streamed_from_llm:
            current_time = time.time()
            if current_time - start_time > max_wait_time:
                logger.info("Maximum wait time reached, proceeding to push to SQS.")
                break
            time.sleep(1)  # Check the flag every second
        handle_post_streaming()

    query_text = request.args.get('query_text', '')
    ids_string = request.args.get('ids', '')
    search_id = request.args.get('search_id', '')
    logger.info(f'ids are {ids_string} for search_id {search_id}')
    ids_list = ids_string.split(',') if ids_string else []
    ids_list = [str(x) for x in ids_list]
    logger.info(f'ids are {ids_list}')
    # query and ids should be available
    if not query_text or not ids_list:  # Handle error case
        stream = stream_error(query_text)
    else:  # Handle valid case
        sm_request_dict = SummaryService.create_prompt_request_params_summary(query=query_text, top_article_ids=ids_list, token_limit=4096)
        stream = stream_sagemaker(sm_request_dict)

    res = Response(stream_with_context(stream), mimetype='text/event-stream')
    # Start the background task with dynamic wait
    threading.Thread(target=background_task_with_dynamic_wait).start()
    return res


@application.route('/summarize_search_v1', methods=['GET'])
def summarize_search_results_new():
    streamed_summary = []
    summary_streamed_from_llm = False
    llm_name = 'OpenHermes-Search-UkuleleZebraWillow'
    my_config = Config(
        region_name='ap-south-1',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        },
        max_pool_connections=40  # Increase the pool size
    )

    # Create a SageMaker Runtime client with the custom configuration
    sess1 = boto3.session.Session()
    sagemaker_runtime = sess1.client("sagemaker-runtime", config=my_config)

    def stream_openai(sys_pmt, usr_pmt):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        model = 'gpt-4-0125-preview'
        llm_name = model
        print('streaming openai')
        res = openai_client.chat.completions.create(model=model, messages=[{'role': 'system', 'content': sys_pmt}, {'role': 'user', 'content': usr_pmt}], stream=True)
        for chunk in res:
            cur_content = chunk.choices[0].delta.content
            if cur_content:
                streamed_token = cur_content if cur_content != "\n" else "<br>"
                streamed_summary.append(streamed_token)
                yield f"{cur_content}"
        summary_streamed_from_llm = True

    def stream_claude(sys_pmt, usr_pmt):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        model = 'claude-3-sonnet-20240229'
        llm_name = model
        print('streaming claude')
        with anthropic_client.messages.stream(model=model, max_tokens=768, messages=[{'role': 'user', 'content': f'{sys_pmt}. query: {usr_pmt}'}]) as stream:
            for cur_content in stream.text_stream:
                streamed_token = cur_content if cur_content != "\n" else "<br>"
                streamed_summary.append(streamed_token)
                yield f"{cur_content}"

    # def stream_claude(sys_pmt, usr_pmt):
    #     nonlocal streamed_summary, summary_streamed_from_llm, llm_name
    #     model = 'claude-3-haiku-20240307'
    #     llm_name = model
    #     print('streaming claude')
    #     res = openai_client.chat.completions.create(model=model, messages=[{'role': 'system', 'content': sys_pmt}, {'role': 'user', 'content': usr_pmt}], stream=True)
    #     for chunk in res:
    #         cur_content = chunk.choices[0].delta.content
    #         if cur_content:
    #             streamed_token = cur_content if cur_content != "\n" else "<br>"
    #             streamed_summary.append(streamed_token)
    #             yield f"{cur_content}"
    #     summary_streamed_from_llm = True

    def stream_sagemaker(rqst):
        nonlocal streamed_summary, summary_streamed_from_llm
        # if 'web_sources' in rqst:
        #     web_sources = rqst.pop('web_sources')
        #     logger.info(f'web search sources are {web_sources}')
        response = sagemaker_runtime.invoke_endpoint_with_response_stream(
            EndpointName='OpenHermes-Search-UkuleleZebraWillow',
            Body=json.dumps(rqst),
            ContentType="application/json",
        )
        for token in TokenIterator(response["Body"]):
            streamed_token = token if token != "\n" else "<br>"
            streamed_summary.append(streamed_token)
            yield streamed_token
        summary_streamed_from_llm = True

    def stream_error(query):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        message = f'''I am sorry, but I am unable to assist you with your query of {query}.<br>As a financial assistant AI developed by the **Insight** team, my expertise is tailored specifically to address inquiries related to Indian finance. Please feel free to ask me any questions within this domain, and I'll do my best to provide you with the information you need 🚀.'''
        streamed_summary = [message]
        llm_name = ''
        for word in message.split(" "):  # Splitting the message into words
            sleep(0.01)
            yield f"{word} "
        summary_streamed_from_llm = True

    def handle_post_streaming():
        complete_response = ''.join(streamed_summary)
        if search_id:
            response_object = {'search_id': search_id, 'summary_info': {'streamed_summary': complete_response,
                                                                        'llm_name': llm_name}}
            logger.info(f'will be logging {response_object} for search_id {search_id}')
            sqs_response = sqs.send_message(QueueUrl=summary_queue_url, MessageBody=json.dumps(response_object))
            logger.info(f'response from sqs for {search_id} is {sqs_response}')

    def background_task_with_dynamic_wait():
        max_wait_time = 30  # Maximum time to wait in seconds
        start_time = time.time()
        while not summary_streamed_from_llm:
            current_time = time.time()
            if current_time - start_time > max_wait_time:
                logger.info("Maximum wait time reached, proceeding to push to SQS.")
                break
            time.sleep(1)  # Check the flag every second
        handle_post_streaming()

    def eligible_for_openai():
        time_eligible = datetime.now().minute % 10 >= 5
        # user_eligible = user_id in ['99', 99, '98', 98, 105, '105', '120', 120, '170', 170, 1, '1']
        return time_eligible

    query_text = request.args.get('query_text', '')
    ids_string = request.args.get('ids', '')
    search_id = request.args.get('search_id', '')
    user_id = request.args.get('userId', '')
    logger.info(f'user_id is {user_id}')
    logger.info(f'ids are {ids_string} for search_id {search_id}')
    ids_list = ids_string.split(',') if ids_string else []
    ids_list = [str(x) for x in ids_list]
    logger.info(f'ids are {ids_list}')
    # query and ids should be available
    if not query_text or not ids_list:  # Handle error case
        stream = stream_error(query_text)
    else:
        internal_users = ['1', '98', '99', '105', '120', '170', '196']
        use_citations = str(user_id) in internal_users
        sys_prompt, usr_prompt = SummaryService.create_web_search_prompt_for_openai(search_query=query_text, references_article_ids=ids_list, token_limit=4096, use_citations=True)
        stream = stream_openai(sys_prompt, usr_prompt)
        # stream = stream_claude(sys_prompt, usr_prompt)
    # else:  # Handle valid case
    #     sm_request_dict = SummaryService.create_prompt_request_params_summary(query=query_text, top_article_ids=ids_list, token_limit=6144)
    #     logger.info(f'prompt is {sm_request_dict}')
    #     stream = stream_sagemaker(sm_request_dict)

    res = Response(stream_with_context(stream), mimetype='text/event-stream')
    # Start the background task with dynamic wait
    threading.Thread(target=background_task_with_dynamic_wait).start()
    return res


@application.route('/summarize_portfolio_search', methods=['GET'])
def summarize_search_results_portfolio_web():
    streamed_summary = []
    summary_streamed_from_llm = False
    llm_name = 'gpt-4-0125-preview'

    def stream_openai(sys_pmt, usr_pmt):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        model = 'gpt-4-0125-preview'
        llm_name = model
        print('streaming openai')
        res = openai_client.chat.completions.create(model=model, messages=[{'role': 'system', 'content': sys_pmt}, {'role': 'user', 'content': usr_pmt}], stream=True)
        for chunk in res:
            cur_content = chunk.choices[0].delta.content
            if cur_content:
                streamed_token = cur_content if cur_content != "\n" else "<br>"
                streamed_summary.append(streamed_token)
                yield f"{cur_content}"
        summary_streamed_from_llm = True

    def stream_claude(sys_pmt, usr_pmt):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        model = 'claude-3-haiku-20240307'
        llm_name = model
        print('streaming openai')
        with anthropic_client.messages.stream(model=model, max_tokens=768, messages=[{'role': 'user', 'content': f'{sys_pmt}. {usr_pmt}'}]) as stream:
            for cur_content in stream.text_stream:
                streamed_token = cur_content if cur_content != "\n" else "<br>"
                streamed_summary.append(streamed_token)
                yield f"{cur_content}"
        # for chunk in res:
        #     cur_content = chunk.choices[0].delta.content
        #     if cur_content:
        #         streamed_token = cur_content if cur_content != "\n" else "<br>"
        #         streamed_summary.append(streamed_token)
        #         yield f"{cur_content}"
        summary_streamed_from_llm = True

    def stream_error(query, uid, error_type='non_financial'):
        nonlocal streamed_summary, summary_streamed_from_llm, llm_name
        non_financial_message = f'''I am sorry, but I am unable to assist you with your query of {query}.<br>As a financial assistant AI developed by the **Insight** team, my expertise is tailored specifically to address inquiries related to Indian finance. Please feel free to ask me any questions within this domain, and I'll do my best to provide you with the information you need 🚀.'''
        no_portfolio_found_message_app = f'''To get insights related to your portfolio, please link your smallcase account in the 'money' tab'''
        no_portfolio_found_message_vercel = f'''Personalized portfolio insights are only supported on our **Insight** app. Please wait list your self to get access and get many more insights'''
        if error_type == 'portfolio_not_found':
            if uid == '121':
                streamed_summary = [no_portfolio_found_message_vercel]
            else:
                streamed_summary = [no_portfolio_found_message_app]
        else:
            streamed_summary = [non_financial_message]
        llm_name = ''
        for word in non_financial_message.split(" "):  # Splitting the message into words
            sleep(0.01)
            yield f"{word} "
        summary_streamed_from_llm = True

    def handle_post_streaming():
        complete_response = ''.join(streamed_summary)
        if search_id:
            response_object = {'search_id': search_id, 'summary_info': {'streamed_summary': complete_response,
                                                                        'llm_name': llm_name}}
            logger.info(f'will be logging {response_object} for search_id {search_id}')
            sqs_response = sqs.send_message(QueueUrl=summary_queue_url, MessageBody=json.dumps(response_object))
            logger.info(f'response from sqs for {search_id} is {sqs_response}')

    def background_task_with_dynamic_wait():
        max_wait_time = 30  # Maximum time to wait in seconds
        start_time = time.time()
        while not summary_streamed_from_llm:
            current_time = time.time()
            if current_time - start_time > max_wait_time:
                logger.info("Maximum wait time reached, proceeding to push to SQS.")
                break
            time.sleep(1)  # Check the flag every second
        handle_post_streaming()

    def eligible_for_openai():
        time_eligible = datetime.now().minute % 10 >= 5
        # user_eligible = user_id in ['99', 99, '98', 98, 105, '105', '120', 120, '170', 170, 1, '1']
        return time_eligible

    def reduce_portfolio_data(portfolio_dict):
        if not portfolio_dict:
            return []
        data = list(portfolio_dict[0].values())[0]['data']
        truncated_data = {}
        for element in data:
            for k, v in element.items():
                if len(v) < 10:
                    truncated_data[k] = v
                else:
                    if isinstance(v, dict):
                        all_keys = sorted(list(v.keys()))
                        random_keys = list(np.random.choice(all_keys, 10))
                        random_keys.append(all_keys[0])
                        random_keys.append(all_keys[-1])
                        random_keys = sorted(list(set(random_keys)))
                        truncated_data[k] = {k1: v[k1] for k1 in random_keys}
                    elif isinstance(v, list):
                        truncated_data[k] = np.random.choice(v, 10)
        return truncated_data

    query_text = request.args.get('query_text', '')
    ids_string = request.args.get('ids', '')
    user_portfolio_data_request = request.args.get('user_portfolio_data', '')
    portfolio_data_string = request.args.get('portfolio_data', '')
    search_id = request.args.get('search_id', '')
    user_id = request.args.get('userId', '')
    user_id = str(user_id)
    try:
        portfolio_data = json.loads(portfolio_data_string)
        portfolio_data = reduce_portfolio_data(portfolio_dict=portfolio_data)
        logger.info(portfolio_data)
    except:
        portfolio_data = [{'dummy_key': 'dummy_value'}]

    logger.info(f'portfolio_data_string is {portfolio_data_string}')
    logger.info(f'user_id is {user_id}')
    logger.info(f'ids are {ids_string} for search_id {search_id}')
    logger.info(f'portfolio_data is {portfolio_data}')

    ids_list = ids_string.split(',') if ids_string else []
    ids_list = [str(x) for x in ids_list]
    logger.info(f'ids are {ids_list}')
    internal_users = ['1', '98', '99', '105', '120', '170', '196']
    is_internal_user = str(user_id) in internal_users
    # query and ids should be available
    if not query_text or (not ids_list and not portfolio_data):  # Handle error case
        if user_portfolio_data_request and not portfolio_data:   # user has requested for portfolio data, but that is not found
            stream = stream_error(query_text, uid=user_id, error_type='portfolio_not_found')
        else:   # this is when there are no ids
            stream = stream_error(query_text, uid=user_id, error_type='articles_not_found')  # TODO: - doesn't seem like exhaustive case
    elif portfolio_data:     # portfolio data exists
        sys_prompt, usr_prompt = SummaryService.create_portfolio_summary_prompt_for_claude(user_query=query_text, portfolio_response=json.dumps(portfolio_data))
        # sys_prompt, usr_prompt = SummaryService.create_web_search_prompt_for_openai(search_query=query_text, references_article_ids=ids_list, token_limit=4096, use_citations=True)
        stream = stream_openai(sys_prompt, usr_prompt)
    elif ids_list:
        sys_prompt, usr_prompt = SummaryService.create_web_search_prompt_for_openai(search_query=query_text, references_article_ids=ids_list, token_limit=4096, use_citations=True)
        if is_internal_user:
            stream = stream_openai(sys_prompt, usr_prompt)
        else:
            stream = stream_openai(sys_prompt, usr_prompt)
    # else:  # Handle valid case
    #     sm_request_dict = SummaryService.create_prompt_request_params_summary(query=query_text, top_article_ids=ids_list, token_limit=6144)
    #     logger.info(f'prompt is {sm_request_dict}')
    #     stream = stream_sagemaker(sm_request_dict)

    res = Response(stream_with_context(stream), mimetype='text/event-stream')
    # Start the background task with dynamic wait
    threading.Thread(target=background_task_with_dynamic_wait).start()
    return res

#
#
# @application.route('/get_search_summary', methods=['GET'])
# def get_search_summary():
#     query_text = request.args.get('query_text', '')
#     query_text = clean_search_query(query_text)
#     if not query_text:
#         return []
#     is_fin, recency_weight, improved_query = QueryService.understand_query_using_llm(query_text=query_text)
#     if not is_fin:
#         return f'''I apologize, but I am unable to assist you with {query_text}. As a financial assistant AI developed by Insight, my expertise is tailored specifically to address inquiries related to Indian finance. Please feel free to ask me any questions within this domain, and I'll do my best to provide you with the information you need.'''
#     if improved_query:
#         search_response_object = HybridSearchService.perform_hybrid_reranked_search(query_text=improved_query, recency_importance=recency_weight)
#     else:
#         search_response_object = HybridSearchService.perform_hybrid_reranked_search(query_text=query_text, recency_importance=recency_weight)
#     top_article_ids = [x['article_id'] for x in search_response_object['searchArticleIds'][:3]]
#     my_config = Config(
#         region_name='ap-south-1',
#         retries={
#             'max_attempts': 3,
#             'mode': 'standard'
#         },
#         max_pool_connections=40  # Increase the pool size
#     )
#
#     # Create a SageMaker Runtime client with the custom configuration
#     sess1 = boto3.session.Session()
#     sagemaker_runtime = sess1.client("sagemaker-runtime", config=my_config)
#
#     def stream_sagemaker(rqst):
#         response = sagemaker_runtime.invoke_endpoint_with_response_stream(
#             EndpointName='OpenHermes-Search-MangoPurpleValley',
#             Body=json.dumps(rqst),
#             ContentType="application/json",
#         )
#         for token in TokenIterator(response["Body"]):
#             yield f"{token}"
#
#     logger.info(f'ids are {top_article_ids}')
#     # query and ids should be available
#     if not query_text or not top_article_ids:
#         return f'''
#             I apologize, but I am unable to assist you with {query_text}. As a financial assistant AI developed by Insight, my expertise is tailored specifically to address inquiries related to Indian finance. Please feel free to ask me any questions within this domain, and I'll do my best to provide you with the information you need.
#             '''
#     sm_request_dict = SummaryService.create_prompt_request_params_summary(query=query_text, top_article_ids=top_article_ids)
#     return Response(stream_sagemaker(rqst=sm_request_dict), mimetype='text/event-stream')


if __name__ == '__main__':
    application.debug = False
    application.run(host="0.0.0.0", port=8000)

# @application.route('/find_source_wise_count', methods=['POST'])
# def get_source_count():
#     docs = mongo_conn.fetch_article_published_time_df(collection_name='articles', db_name='insight_db')
#     count_dict = {}
#     for doc in docs:
#         source_id = doc.get('source_id')
#         if source_id:
#             if source_id not in count_dict:
#                 count_dict[source_id] = 0
#             count_dict[source_id] += 1
#     print(count_dict)
#     return jsonify(count_dict)
