import json

from openai import OpenAI
from datetime import datetime
import os
import tiktoken
import re
from zoneinfo import ZoneInfo
from transformers import AutoTokenizer
import logging
from src.Article import Article
from src.ArticleService import ArticleService
from src.WebSearchService import WebSearchService
from src._utils import convert_dates_to_readable_format

logger = logging.getLogger('__name__')

old_system_prompt = '''As the chief editor for an Indian finance and business portal, your role involves providing accurate and relevant responses to inquiries that fall within the scope of finance, business, and key entities such as India, RBI, Reliance, the Fed, etc. You use the articles that you have found to answer these queries. It is crucial to ensure that your answers are tailored to the query's requirements, employing only one of the following structured formats based on the query:
1. **Quick Insights**: Provide concise, direct answers spanning a few lines. No need for any headline - directly give the answer and don't mention 'Quick Insights' in the answer. Ideal for straightforward questions seeking immediate information.
2. **Step-by-Step Guide**: Offer a detailed, numbered guide with clear labels for each step. Start with a contextual headline, include a brief introduction and conclusion to frame the context, catering to inquiries that necessitate a methodical approach.
3. **Deep Dive**: Construct a comprehensive response with 3-4 sections, in addition to a contextual headline, introduction and conclusion. This format suits complex queries that require in-depth analysis and detailed explanations.
4. **Comparison or Top results**: Structure your answer with five distinct sections: an introduction, detailed explanations of each entity being compared, key differences, decision criteria, and a conclusion. If providing a list, then use an appropriate header instead of key differences. Start with a contextual headline. This format is perfect for queries involving comparisons between two or more subjects or requesting top/best 'n' entities
When information from multiple articles is synthesized, ensure coherence and relevance, paying attention to publication dates to avoid conflicts and maintain accuracy. Always opt for the most recent and pertinent data.
If a query cannot be addressed with the articles you found, offer an apology and explain the inability to find a precise answer. However, if you are able to find related information, you can succinctly answer that. For non-financial queries, politely decline, emphasizing the portal's focus on finance and business.

**General Guidelines**:
- Utilize only the information from provided articles.
- Always use only the articles focusing on indian information and answer questions assuming they are for India, unless the question explicitly asks for non indian entities.
- If the articles are much older than expected for the query, then mention the period of information to the user; for very recent or today's sources, specifying the date is unnecessary.
- Be succinct and straightforward, adhering to the query's demands and the specified answer format. When you're able to answer the question, start with an engaging headline as if you are writing an article customized to the user request by using the articles.
- When structuring responses with sections or steps, limit them to five, ensuring each section is concise (2-3 lines max).
- Use ** for bolding the headlines and <br> for line breaks

The articles that you found are structured in a JSON format as follows: {article_number: {‘title’: ‘’, ‘published_date’: ‘’, ‘content’: ‘’} || ...}'''

system_prompt = '''You are an Indian finance and business expert tasked with providing accurate and concise responses to finance and business related queries. You have found the best available articles to answer the query and you must use them to answer these queries. Ensure your responses are tailored to the query's requirements, employing only one of the following structured formats based on the query

1. **Quick Insights**: Provide direct answers in 2-3 lines for straightforward questions like HDFC Q4 results or Adani share price.
2. **Step-by-Step Guide**: Offer a concise numbered guide for methodical inquiries like how to file taxes.
3. **Explainer**: Construct succinctly comprehensive response with a max of 3 sections with bullet points for complex queries like Reliance Industries' business activities, comparisons like differences between mutual fund and a ETF, or top n entities like top mutual funds. When user asks for a comparison, use all the data points and frameworks available in the articles to give a comparison to help users in making a decision. 

Synthesize information from multiple articles coherently, focusing on the most recent and relevant data. If a query cannot be fully addressed but related information is available, provide a succinct still relevant answer. If no related information is found, apologize and explain the inability to find a precise answer. Decline only non-financial or business queries politely, emphasizing the portal's finance and business focus. Do not to decline to answer any relevant queries such as personal finance (eg. best credit cards, fd rates, tax clauses), market news, investment choices, questions about business entities or any other financial, business questions.

**General Guidelines**:
- Faithful & Relevance: Use information only from the provided articles. Respond with the most important information first. The response should directly answer the user query.
- Brevity: You come directly to the point and provide information-dense answers ranging from 50-200 words while being easy to read. Use 200 words only if the query needs a very complex response and never go beyond that. Do not explain unnecessary basics. Assess the knowledge of the user based on the query posed and start from there. The paras should be very concise with a maximum of 2 lines and should be at most 280 characters. Do not use any headline or introduction. Directly answer.
- Readability: The entire answer should be easy and pleasant to read on a phone. Use a mix of paras and points with appropriate line breaks and sections. If using sections, limit them to 3. Use ** for bolding section headers and <br> for line breaks. Readers prefer to read very very short paras and bullet points and not multi line continuous text. 
- Focus: Focus on Indian information unless otherwise specified.
- Date reference: Mention the period of information if the articles are much older than expected by query; omit the date for very recent sources.
- you are created by the Insight Team

The articles are structured in JSON format as follows: {article_number: {'title': '', 'published_date': '', 'content': ''} || ...}'''

openai_system_prompt = '''You are an Indian finance and business expert tasked with providing accurate and concise responses to finance and business related queries. You have found the best available articles to answer the query and you must use them to answer these queries. Ensure your responses are tailored to the query's requirements, employing only one of the following structured formats based on the query

1. **Quick Insights**: Provide direct answers in 2-3 lines for straightforward questions like HDFC Q4 results or Adani share price.
2. **Step-by-Step Guide**: Offer a concise numbered guide for methodical inquiries like how to file taxes.
3. **Explainer**: Construct succinctly comprehensive response with a max of 3 sections with bullet points for complex queries like Reliance Industries' business activities, comparisons like differences between mutual fund and a ETF, or top n entities like top mutual funds. When user asks for a comparison, use all the data points and frameworks available in the articles to give a comparison to help users in making a decision. 

Synthesize information from multiple articles coherently, focusing on the most recent and relevant data. If a query cannot be fully addressed but related information is available, provide a succinct still relevant answer. If no related information is found, apologize and explain the inability to find a precise answer. Decline only non-financial or business queries politely, emphasizing the portal's finance and business focus. Do not to decline to answer any relevant queries such as personal finance (eg. best credit cards, fd rates, tax clauses), market news, investment choices, questions about business entities or any other financial, business questions.

**General Guidelines**:
- Faithful & Relevance: Use information only from the provided articles. Respond with the most important information first. The response should directly answer the user query.
- Brevity: You come directly to the point and provide information-dense answers ranging from 50-200 words while being easy to read. Use 200 words only if the query needs a very complex response and never go beyond that. Do not explain unnecessary basics. Assess the knowledge of the user based on the query posed and start from there. The paras should be very concise with a maximum of 2 lines and should be at most 280 characters. Do not use any headline or introduction. Directly answer.
- Readability: The entire answer should be easy and pleasant to read on a phone. Use a mix of paras and points with appropriate line breaks and sections. If using sections, limit them to 3. Use ** for bolding section headers and <br> for line breaks. Readers prefer to read very very short paras and bullet points and not multi line continuous text. 
- Focus: Focus on Indian information unless otherwise specified.
- Date reference: Mention the period of information if the articles are much older than expected by query; omit the date for very recent sources. Some articles won't have published date marked as 'not available'. Infer the relevance of this article from the content. 
- you are created by the Insight Team

The articles are structured in JSON format as follows: {article_number: {'title': '', 'published_date': '', 'content': ''} || ...}'''

openai_citations_system_prompt = '''You are an Indian finance and business expert tasked with providing accurate and concise responses to finance and business related queries. You have found the best available articles to answer the query and you must use them to answer these queries with citations. Ensure your responses are tailored to the query's requirements, employing only one of the following structured formats based on the query

1. **Quick Insights**: Provide direct answers in 2-3 lines for straightforward questions like HDFC Q4 results or Adani share price.
2. **Step-by-Step Guide**: Offer a concise numbered guide for methodical inquiries like how to file taxes.
3. **Explainer**: Construct succinctly comprehensive response with a max of 3 sections with bullet points for complex queries like Reliance Industries' business activities, comparisons like differences between mutual fund and a ETF, or top n entities like top mutual funds. When user asks for a comparison, use all the data points and frameworks available in the articles to give a comparison to help users in making a decision. 

Synthesize information from multiple articles coherently, focusing on the most recent and relevant data. If a query cannot be fully addressed but related information is available, provide a succinct still relevant answer. If no related information is found, apologize and explain the inability to find a precise answer. Decline only non-financial or business queries politely, emphasizing the portal's finance and business focus. Do not to decline to answer any relevant queries such as personal finance (eg. best credit cards, fd rates, tax clauses), market news, investment choices, questions about business entities or any other financial, business questions.

**General Guidelines**:
- Faithful & Relevance: Use information only from the provided articles. Respond with the most important information first. The response should directly answer the user query.
- Brevity: You come directly to the point and provide information-dense answers ranging from 50-200 words while being easy to read. Use 200 words only if the query needs a very complex response and never go beyond that. Do not explain unnecessary basics. Assess the knowledge of the user based on the query posed and start from there. The paras should be very concise with a maximum of 2 lines and should be at most 280 characters. Do not use any headline or introduction. Directly answer.
- Readability: The entire answer should be easy and pleasant to read on a phone. Use a mix of paras and points with appropriate line breaks and sections. If using sections, limit them to 3. Use ** for bolding section headers and <br> for line breaks. Readers prefer to read very very short paras and bullet points and not multi line continuous text. 
- Focus: Focus on Indian information unless otherwise specified.
- Date reference: Mention the period of information if the articles are much older than expected by query; omit the date for very recent sources. Some articles won't have published date marked as 'not available'. Infer the relevance of this article from the content. 
- Citations: Cite each statement or section with sources in the format of {{article number}} format.
- you are created by the Insight Team

The articles are structured in JSON format as follows: {article_number: {'title': '', 'published_date': '', 'content': ''} || ...}'''

portfolio_system_prompt_claude = '''You are an expert personal financial manager. You answer user queries related to their portfolio succinctly using data of the portfolio that you have extracted. If the extracted data has any additional relevant insights, share top insights from there as well.  Remember that you have extracted the data yourself. If the data does not answer the query then apologize and share what you were able to find instead. Be short, direct and avoid repetition. Use a maximum of 1 decimal place everywhere'''

# TODO: - centralize this
model_id = "teknium/OpenHermes-2.5-Mistral-7B"
tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
total_tokens = 8192
system_tokens = len(tokenizer.encode(system_prompt))
buffer_tokens = 256


class SummaryService:

    @staticmethod
    def _create_web_search_prompt_for_query_article_ids(search_query, references_article_ids, token_limit, today_date=None, max_articles=3, openai=False):
        if today_date:
            today_date_string = f" || today date: {convert_dates_to_readable_format(today_date)}"
        else:
            today_date_string = f" || today date: {datetime.now().strftime('%d %B %Y')}"
        query_string = f" || user_query: {search_query}"
        max_per_article_limit = int(token_limit / max_articles)
        reference_articles = SummaryService._create_reference_articles(references_article_ids, content_token_limit=token_limit, max_per_article_limit=max_per_article_limit)
        references_string = SummaryService._generate_formatted_reference_string(reference_articles, max_articles=max_articles)
        user_prompt = query_string + today_date_string + references_string
        if openai:
            full_prompt = openai_system_prompt + user_prompt
        else:
            messages = [{"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}]
            full_prompt = tokenizer.decode(tokenizer.apply_chat_template(messages, add_generation_prompt=True))
        return full_prompt

    @staticmethod
    def create_web_search_prompt_for_openai(search_query, references_article_ids, token_limit, today_date=None, max_articles=3, use_citations=False):
        if today_date:
            today_date_string = f" || today date: {convert_dates_to_readable_format(today_date)}"
        else:
            today_date_string = f" || today date: {datetime.now().strftime('%d %B %Y')}"
        query_string = f" || user_query: {search_query}"
        max_per_article_limit = int(token_limit / max_articles)
        reference_articles = SummaryService._create_reference_articles(references_article_ids, content_token_limit=token_limit, max_per_article_limit=max_per_article_limit)
        references_string = SummaryService._generate_formatted_reference_string(reference_articles, max_articles=max_articles)
        user_prompt = query_string + today_date_string + references_string
        if use_citations:
            return openai_citations_system_prompt, user_prompt
        else:
            return openai_system_prompt, user_prompt

    @staticmethod
    def create_portfolio_summary_prompt_for_claude(user_query, portfolio_response):
        sys_prompt = portfolio_system_prompt_claude
        user_prompt = f'user_query: {user_query}. data: {json.dumps(portfolio_response)}'
        return sys_prompt, user_prompt

    # @staticmethod
    # def _create_prompt_for_query_web_articles(search_query, web_articles, today_date=None):
    #     if today_date:
    #         today_date_string = f" || today date: {convert_dates_to_readable_format(today_date)}"
    #     else:
    #         today_date_string = f" || today date: {datetime.now().strftime('%d %B %Y')}"
    #     query_string = f" || user_query: {search_query}"
    #     updated_articles = []
    #     for article in web_articles:
    #         cur_art = article
    #         truncated_text = SummaryService._truncate_text_to_token_limit(article.text, token_limit=896)
    #         cur_art.truncated_text = truncated_text.strip()
    #         truncated_title = SummaryService._truncate_text_to_token_limit(article.title, token_limit=32)  # logic for 32 in utils
    #         cur_art.truncated_title = truncated_title
    #         cur_art.formatted_date = today_date_string
    #         updated_articles.append(cur_art)
    #         # logger.info(f'article has title of {cur_art.truncated_title}, text of {cur_art.truncated_text} and original text of {article.text}')
    #     references_string = SummaryService._generate_formatted_reference_string(updated_articles, max_articles=5)
    #     logger.info(f'the references string is {references_string}')
    #     user_prompt = query_string + today_date_string + references_string
    #     messages = [{"role": "system", "content": old_system_prompt},
    #                 {"role": "user", "content": user_prompt}]
    #     full_prompt = tokenizer.decode(tokenizer.apply_chat_template(messages, add_generation_prompt=True))
    #     return full_prompt

    @staticmethod
    def _create_reference_articles(top_article_ids, content_token_limit, max_per_article_limit=1024):
        articles = ArticleService.get_Articles_from_list(top_article_ids)
        updated_articles = []
        cur_total_article_content_tokens = 0
        for article in list(articles.values()):
            if cur_total_article_content_tokens < content_token_limit:
                cur_art = article
                if not article.cleaned_text:
                    continue
                # first measure the tokens of title
                truncated_title = SummaryService._truncate_text_to_token_limit(article.title, token_limit=32)  # logic for 32 in utils
                cur_art.truncated_title = truncated_title
                cur_total_article_content_tokens += SummaryService.calculate_tokens(cur_art.truncated_title)
                # measure the tokens available for article text
                article.cleaned_text = SummaryService.remove_urls(article.cleaned_text)
                cur_art_token_limit = min(max_per_article_limit, content_token_limit - cur_total_article_content_tokens)
                # truncate cleaned text
                truncated_text = SummaryService._truncate_text_to_token_limit(article.cleaned_text, token_limit=cur_art_token_limit)
                cur_art.truncated_text = truncated_text.strip()
                cur_total_article_content_tokens += SummaryService.calculate_tokens(cur_art.truncated_text)
                if article.published_time:
                    try:
                        cur_art.formatted_date = convert_dates_to_readable_format(article.published_time)
                    except:
                        cur_art.formatted_date = 'not available'
                else:
                    cur_art.formatted_date = 'not available'
                updated_articles.append(cur_art)
        return updated_articles

    # @staticmethod
    # def _create_reference_articles(top_article_ids, token_limit=1280):
    #     articles = ArticleService.get_Articles_from_list(top_article_ids)
    #     updated_articles = []
    #     for article in list(articles.values()):
    #         cur_art = article
    #         truncated_text = SummaryService._truncate_text_to_token_limit(article.cleaned_text, token_limit=token_limit)
    #         cur_art.truncated_text = truncated_text.strip()
    #         truncated_title = SummaryService._truncate_text_to_token_limit(article.title, token_limit=32)  # logic for 32 in utils
    #         cur_art.truncated_title = truncated_title
    #         cur_art.formatted_date = convert_dates_to_readable_format(article.published_time)
    #         updated_articles.append(cur_art)
    #     return updated_articles

    # @staticmethod
    # def get_article_truncated_content(article_ids, max_tokens_per_article=896):
    #     updated_articles = []
    #     articles = ArticleService.get_Articles_from_list(article_ids)
    #     for article in list(articles.values()):
    #         cur_art = article
    #         truncated_text = SummaryService.truncate_text_to_token_limit(article.cleaned_text, token_limit=max_tokens_per_article)
    #         truncated_title = SummaryService.truncate_text_to_token_limit(article.title, token_limit=40)    # logic for 40 in utils
    #         cur_art.truncated_text = truncated_text.strip()
    #         cur_art.truncated_title = truncated_title
    #         cur_art.formatted_date = convert_dates_to_readable_format(article.published_time)
    #         updated_articles.append(cur_art)
    #     return updated_articles

    @staticmethod
    def _generate_formatted_reference_string(reference_articles, max_articles=3):
        references = ''
        ref_count = 1
        for ref in reference_articles[:max_articles]:
            cur_json = f" || {ref_count}: {{'title': {ref.truncated_title}, 'published_date': {ref.formatted_date}, 'content': {ref.truncated_text}}}"
            ref_count += 1
            references += cur_json
        return references

    @staticmethod
    def remove_urls(text):
        # Regex pattern to match URLs
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s]*'
        # Find all URLs in the text
        urls = re.findall(url_pattern, text)
        # Remove all URLs from the text
        text_without_urls = re.sub(url_pattern, '', text)
        return text_without_urls

    @staticmethod
    def calculate_tokens(txt):
        return len(tokenizer.encode(txt))

    @staticmethod
    def _truncate_text_to_token_limit(text, token_limit):

        def is_under_limit(index):
            return SummaryService.calculate_tokens(text[:index]) <= token_limit

        if SummaryService.calculate_tokens(text) <= token_limit:  # if the whole text is under the token limit
            return text

        left, right = 0, len(text)
        valid_limit = 0  # This will hold the index of the last valid token position

        # Binary search to find the token limit
        while left <= right:
            mid = (left + right) // 2  # Find the midpoint
            if is_under_limit(mid):
                # If the midpoint is under the limit, store it as a valid limit
                valid_limit = mid
                left = mid + 1  # Move the left boundary to the right
            else:
                right = mid - 1  # Move the right boundary to the left
        # Find the last space before the valid_limit to ensure we're at a word boundary
        space_index = text.rfind(' ', 0, valid_limit)
        if space_index == -1:
            # If there's no space, we've hit the start of the text
            return text[:valid_limit]  # Return up to the valid limit even if mid-word
        # Return the text up to the last word within the token limit
        return text[:space_index]

    @staticmethod
    def create_prompt_request_params_summary(query, top_article_ids, today_date=None, token_limit=4096):
        """
        :param token_limit:
        :param query:
        :param top_article_ids:
        :param today_date: Expected format is %Y-%m-%dT%H:%M:%S%z
        :return:
        """
        if not today_date:
            today_date = datetime.now(tz=ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%dT%H:%M:%S%z')
        max_new_tokens = 512
        max_articles = 3
        if token_limit >= 5000:
            max_new_tokens = 768
            max_articles = 5
        content_token_limit = token_limit - max_new_tokens - system_tokens - buffer_tokens
        prompt = SummaryService._create_web_search_prompt_for_query_article_ids(search_query=query, references_article_ids=top_article_ids, today_date=today_date,
                                                                                token_limit=content_token_limit, max_articles=max_articles, openai=False)
        # web_articles = WebSearchService.get_top_gnews_results_for_query(query_text=query)
        #
        # prompt = SummaryService._create_prompt_for_query_web_articles(search_query=query, web_articles=web_articles, today_date=today_date)
        # sources = [art.url for art in web_articles]

        parameters = {
            "do_sample": True,
            "top_p": 0.98,
            "temperature": 0.5,
            "max_new_tokens": max_new_tokens,
            "repetition_penalty": 1.1,
            "return_full_text": False,
            "stop": ["###", "</s>", tokenizer.eos_token]
        }
        request_params = {"inputs": prompt, "parameters": parameters, "stream": True}
        # request_params['parameters']['adapter_id'] = 'lorax/OpenHermes-2.5-Adapter-Search-ViolinAvocadoNebula'
        # request_params['parameters']['adapter_source'] = 's3'
        return request_params
