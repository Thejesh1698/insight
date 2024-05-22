import requests
import pandas as pd
import json
import numpy as np
import time
from datetime import datetime, timedelta, timezone
from requests.auth import HTTPBasicAuth
import os
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from transformers import AutoTokenizer

from src.ArticleService import ArticleService
from src.EmbeddingsService import EmbeddingsService
from sql.SearchSQL import SearchSQL
from tqdm.notebook import tqdm

from src.HybridSearchService import HybridSearchService
from src.QueryService import QueryService
from src.SummaryService import SummaryService
from src._utils import convert_dates_to_readable_format

ES_URL = f'https://{os.environ.get("ES_HOST")}/finance-content/_search'
embedding_service = EmbeddingsService(hf_model_path='BAAI/bge-large-en-v1.5')
SYS_PROMPT_OLD = '''You are an Indian finance and business expert and your role involves providing accurate and relevant responses to inquiries that fall within the scope of finance, business, and key entities such as India, RBI, Reliance, the Fed, etc. You use the articles that you have found to answer these queries with citations. It is crucial to ensure that your answers are tailored to the query's requirements, employing only one of the following structured formats based on the query:
1. **Quick Insights**: Provide concise, direct answers spanning a few lines. directly give the answer within 2-3 lines without any headline or section name . Ideal for straightforward questions seeking immediate information like hdfc q4 results or Adani share price.
2. **Step-by-Step Guide**: Offer a detailed, numbered guide with clear labels for each step. Ideal for inquiries that necessitate a methodical approach like how to file taxes.
3. **Deep Dive**: Construct a comprehensive response with 3-4 sections. This format suits complex queries that require in-depth analysis and detailed explanations like what is Bajaj finance doing as a business.
4. **Comparison or Top results**: Structure your answer with 3 distinct sections: detailed explanations of each entity being compared, key differences and decision criteria. If providing a list, then use an appropriate header instead of key differences. This format is perfect for queries involving comparisons between two or more subjects or requesting top/best 'n' entities like top mutual funds or Bajaj finance vs Bajaj finserv

When information from multiple articles is synthesized, ensure coherence and relevance, paying attention to publication dates to avoid conflicts and maintain accuracy. Always opt for the most recent and pertinent data.
If a query cannot be addressed with the articles you found but if you are able to find related information, you can succinctly answer that. If no related information is available, then offer an apology and explain the inability to find a precise answer. For non-financial queries, politely decline, emphasizing the portal's focus on finance and business.

**General Guidelines**:
- Utilize only the information from provided articles.
- Make the answer information dense while being concise. Your answer should range from 50-200 words while communicating the most important information to answer the query. Do not use any headline. Directly answer.
- Cite each statement or section with sources in the format of {{1}}{{2}}, citing the article numbers from which this information is extracted. Citations are very critical. 
- Always use only the articles focusing on indian information and answer questions assuming they are for India, unless the question explicitly asks for non indian entities.
- If the articles are much older than expected for the query, then mention the period of information to the user; for very recent or today's sources, specifying the date is unnecessary.
- When structuring responses with sections or steps, limit them to 3, ensuring each section is concise (1-2max).
- Use ** for bolding any section headers and <br> for line breaks

The articles that you found are structured in a JSON format as follows: {article_number: {‘title’: ‘’, ‘published_date’: ‘’, ‘content’: ‘’} || ...}'''


SYS_PROMPT = '''You are an Indian finance and business expert tasked with providing accurate and concise responses to finance and business-related queries, particularly those involving key entities like India, RBI, Reliance, and the Fed. You have found the best available articles to answer the query and you must use them to answer these queries. Use the best articles available to answer queries, ensuring your responses are tailored to the query's requirements. Ensure that your answers are tailored to the query's requirements, employing only one of the following structured formats based on the query

1. **Quick Insights**: Provide direct answers in 2-3 lines for straightforward questions like HDFC Q4 results or Adani share price.
2. **Step-by-Step Guide**: Offer a concise numbered guide for methodical inquiries like how to file taxes.
3. **Explainer**: Construct succinctly comprehensive response with a max of 3 sections with bullet points for complex queries like Reliance Industries' business activities, comparisons like differences between mutual fund and a ETF, or top n entities like top mutual funds. When user asks for a comparison, use all the data points and frameworks available in the articles to give a comparison to help users in making a decision. 

Synthesize information from multiple articles coherently, focusing on the most recent and relevant data. If a query cannot be fully addressed but related information is available, provide a succinct answer. If no related information is found, apologize and explain the inability to find a precise answer. Decline non-financial queries politely, emphasizing the portal's finance and business focus.

**General Guidelines**:
- Faithful & Relevance: Use information only from the provided articles. Respond with the most important information first. The response should directly answer the user query.
- Brevity: You come directly to the point and provide information-dense answers ranging from 50-200 words while being easy to read. Use 200 words only if the query needs a very complex response and never go beyond that. Do not explain unnecessary basics. Assess the knowledge of the user based on the query posed and start from there. The paras should be very concise with a maximum of 2 lines and should be at most 280 characters. Do not use any headline or introduction. Directly answer.
- Readability: The entire answer should be easy and pleasant to read on a phone. Use a mix of paras and points with appropriate line breaks and sections. If using sections, limit them to 3. Use ** for bolding section headers and <br> for line breaks. Readers prefer to read very very short paras and bullet points and not multi line continuous text. 
- Focus: Focus on Indian information unless otherwise specified.
- Date reference: Mention the period of information if the articles are much older than expected by query; omit the date for very recent sources.

The articles are structured in JSON format as follows: {article_number: {'title': '', 'published_date': '', 'content': ''} || ...}'''


class TrainingDataGenerator:

    def __init__(self, model_id, queries_df_path, responses_file_path):
        self.queries_df = pd.read_csv(queries_df_path, header=None)
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, use_fast=True)
        self.queries = list(self.queries_df[0].unique())
        self.system_tokens = len(self.tokenizer.encode(SYS_PROMPT))
        self.output_tokens = 768
        self.total_tokens = 5120
        self.max_per_article_limit = 1024
        self.content_tokens = self.total_tokens - self.system_tokens - self.output_tokens - 128
        self.client = OpenAI(api_key=os.environ['OPENAI_KEY'])
        self.gpt_model = 'gpt-4-0125-preview'
        self.best_results = {}
        self.user_prompts = []
        self.responses_file_path = responses_file_path

    def get_best_articles_for_queries(self, max_num_random_dates=3, randomize_num_dates_per_query=True):
        today = datetime.now()
        for q in tqdm(self.queries):
            if randomize_num_dates_per_query:
                cur_num_dates = np.random.randint(1, max_num_random_dates + 1)
            else:
                cur_num_dates = max_num_random_dates
            rand_days = [60 * (x - 0.1) for x in np.random.rand(cur_num_dates)]
            self.best_results[q] = {}
            for num_days in rand_days:
                formatted_dt = (today - timedelta(days=num_days)).strftime('%Y-%m-%dT%H:%M:%S')
                is_fin, recency_weight, improved_query = QueryService.understand_query_using_llm(query_text=q)
                if not is_fin:
                    recency_weight = 'medium'
                a = HybridSearchService.perform_hybrid_reranked_search(query_text=q, recency_importance=recency_weight, max_published_date=formatted_dt, search_n=250, return_n=5)
                self.best_results[q][formatted_dt] = [x['article_id'] for x in a['searchArticleIds']]

    @staticmethod
    def save_results_to_json(data, file_name):
        with open(file_name, 'w') as f:
            json.dump(data, f)

    def _create_reference_articles(self, top_article_ids):
        articles = ArticleService.get_Articles_from_list(top_article_ids)
        updated_articles = []
        cur_total_article_content_tokens = 0
        for article in list(articles.values()):
            if cur_total_article_content_tokens < self.content_tokens:
                cur_art = article
                if not article.cleaned_text:
                    continue
                # first measure the tokens of title
                truncated_title = SummaryService._truncate_text_to_token_limit(article.title, token_limit=32)  # logic for 32 in utils
                cur_art.truncated_title = truncated_title
                cur_total_article_content_tokens += SummaryService.calculate_tokens(cur_art.truncated_title)
                # measure the tokens available for article text
                article.cleaned_text = SummaryService.remove_urls(article.cleaned_text)
                cur_art_token_limit = min(self.max_per_article_limit, self.content_tokens - cur_total_article_content_tokens)
                # truncate cleaned text
                truncated_text = SummaryService._truncate_text_to_token_limit(article.cleaned_text, token_limit=cur_art_token_limit)
                cur_art.truncated_text = truncated_text.strip()
                cur_total_article_content_tokens += SummaryService.calculate_tokens(cur_art.truncated_text)
                cur_art.formatted_date = convert_dates_to_readable_format(article.published_time)
                updated_articles.append(cur_art)
        return updated_articles

    def _generate_user_prompt_for_query(self, search_query, reference_article_ids, today_date=None):
        if today_date:
            today_date_string = f" || today date: {convert_dates_to_readable_format(today_date)}"
        else:
            today_date_string = f" || today date: {datetime.now().strftime('%d %B %Y')}"
        query_string = f" || user_query: {search_query}"
        reference_articles = self._create_reference_articles(reference_article_ids)
        references_string = SummaryService._generate_formatted_reference_string(reference_articles)
        user_prompt = query_string + today_date_string + references_string
        return user_prompt

    def generate_prompts_for_queries(self):
        for q in tqdm(self.best_results):
            for dt in self.best_results[q]:
                cur_prompt = self._generate_user_prompt_for_query(q, reference_article_ids=self.best_results[q][dt], today_date=f'{dt}+0000')
                self.user_prompts.append({'query': q, 'dt': dt, 'sys_prompt': SYS_PROMPT, 'user_prompt': cur_prompt})

    def parse_gpt_api_response(self, query_row, api_response):
        model = api_response.model
        prompt_tokens = api_response.usage.prompt_tokens
        completion_tokens = api_response.usage.completion_tokens
        json_generated = False
        response = api_response.choices[0].message.content
        # Build the dictionary with the required information
        extracted_data = {
            'query': query_row['query'],
            'dt': query_row['dt'],
            'system_prompt': SYS_PROMPT,
            'user_prompt': query_row['user_prompt'],
            'model': model,
            'model_response': json.dumps(response),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens
        }

        return extracted_data

    def fetch_save_attributes(self, query_row):
        res_gpt = self.client.chat.completions.create(model=self.gpt_model, messages=[{'role': 'system', 'content': SYS_PROMPT},
                                                                                  {'role': 'user', 'content': query_row['user_prompt']}])
        parsed_res = self.parse_gpt_api_response(query_row=query_row, api_response=res_gpt)
        self.save_attributes(response_json=parsed_res)
        return True

    def save_attributes(self, response_json):
        cur_df = pd.DataFrame(response_json, index=['i', ])
        cur_df.to_csv(self.responses_file_path, header=None, mode='a')

    def get_gpt4_attributes_for_article_ids(self, fraction=1):
        start_time = time.time()
        valid_responses = 0
        invalid_responses = 0
        num_choice = int(len(self.user_prompts) * fraction)
        shortlisted_rows = np.random.choice(self.user_prompts, num_choice)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.fetch_save_attributes, article_row) for article_row in shortlisted_rows]
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



