from openai import OpenAI
import json
import os
import logging
from src.BingWebSearch import BingWebSearch
from src.HybridSearchService import HybridSearchService
from src.PortfolioService import PortfolioService

client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))

logger = logging.getLogger('__name__')
level = logging.INFO
logger.setLevel(level)


class FunctionCallingService:
    system_prompt = '''You are an expert financial analyst working for a leading indian fintech platform. User queries are either related to their own portfolio (eg. what is the total value of my portfolio or what are my most profitable holdings) or about general financial and business news (eg. how to save taxes or what is the performance of reliance over last 5 years). You extract the following attributes from a given user query. Today is “2024-03-15”. The platform has a database with the following data for user's own portfolio.
    user_portfolio: name, nseticker, holding_quantity, avg_buy_price, current_price
    Based on user's query we'll either run the function search_web_for_query, extract_portfolio_details, calc_growth_rate_for_user_portfolio_companies or get_share_price_history_for_companies
    If user asks for performance of specific companies, then use get_share_price_history_for_companies. However, if the user asks for anything which is more than share price of the company - like fundamental analysis, strengths, weaknesses, earning call results or any other complex queries which need other inputs then use search_web_for_query   
    respond only with the json with the above keys. don't answer the user query directly, but only extract the attributes'''

    @staticmethod
    def parse_details_from_gpt(query, user_id):
        user_prompt = f"user_query: {query}"
        messages = [{"role": "system", "content": FunctionCallingService.system_prompt},
                    {"role": "user", "content": user_prompt}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_web_for_query",
                    "description": "Search web for the user query. To be called when query is not related to analysis of user's own portfolio",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "financial_or_business_query": {"type": "boolean", "description": "If the query is relevant for personal finance, markets of business related queries"},
                            "recency_importance": {"type": "string", "enum": ["high", "medium"],
                                                   "description": "How important is that only most recent articles are fetched. high for very volatile like latest stock prices, medium for slowly changing stuff like regulations or educational and guides"},
                        },
                        "required": ["financial_or_business_query", "recency_importance"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_portfolio_snapshot_details",
                    "description": "Extract details related to user portfolio snapshot - either current or invested",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "aggregation_metric": {"type": "string", "enum": ["current_value", "invested_value", "profit", "profit_percent"],
                                                   "description": "Metric user is requesting for"},
                            "aggregation_level": {"type": "string", "enum": ["overall", "company"],
                                                  "description": "If the user is looking for overall stats or breaking down by company"},
                            "companies_mentioned": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 5,
                                                    "description": "Array of company names mentioned in the user query"},
                            "sorting_order": {"type": "string", "enum": ["ascending", "descending"],
                                              "description": "sorting order requested based on the aggregation_metric. For example user asks for least profitable or most loss making, then sorting order is ascending"}
                        },
                        "required": ["aggregation_metric", "aggregation_level", "companies_mentioned", "sorting_order"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_portfolio_growth_details",
                    "description": "Extract details related to growth rate of user portfolio over a period",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "aggregation_metric": {"type": "string", "enum": ["growth", "growth_over_index"],
                                                   "description": "Metric user is requesting for. If user wants comparison with index, then its growth_over_index else its growth"},
                            "aggregation_level": {"type": "string", "enum": ["overall", "company"],
                                                  "description": "If the user is looking for overall stats or breaking down by company"},
                            "companies_mentioned": {"type": "array", "items": {"type": "string"}, "minItems": 0, "maxItems": 5,
                                                    "description": "Array of company names mentioned in the user query"},
                            "sorting_order": {"type": "string", "enum": ["ascending", "descending"],
                                              "description": "sorting order requested based on the aggregation_metric. For example user asks for least profitable or most loss making, then sorting order is ascending"},
                            "num_days": {"type": "number", "description": "number of days for calculating growth. if nothing is provided, then default is 365 days"}
                        },
                        "required": ["aggregation_metric", "aggregation_level", "companies_mentioned", "sorting_order", "num_days"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_share_price_history_for_companies",
                    "description": "Get the latest and historic share prices for companies. If user does not mention company or asks for sensex or NSE, index or general market - then use NIFTY 50",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "companies_mentioned": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5,
                                                    "description": "Array of company names mentioned in the user query"}
                        },
                        "required": ["companies_mentioned"],
                    },
                },
            }
        ]
        #
        # gpt-4-0125-preview
        model = "gpt-4-0125-preview"
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",  # auto is default, but we'll be explicit
            temperature=0.05
        )
        # return json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        function_name = response.choices[0].message.tool_calls[0].function.name
        arguments = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
        # available_functions = {"search_web_for_query": BingWebSearch.perform_bing_web_search,
        #                        "extract_portfolio_details": PortfolioService.get_current_portfolio_value}
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        evaluation = {'function': {'name': function_name, 'arguments': arguments}}
        query_info = {'model': model, 'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens, 'system_prompt': FunctionCallingService.system_prompt,
                      'user_prompt': {'query': user_prompt, "tools": tools}, 'evaluation': evaluation}
        logger.info(f'query evaluation is {evaluation}')
        if function_name == 'search_web_for_query':
            if not arguments['financial_or_business_query']:
                response = {
                    'searchArticleIds': [],
                    'user_portfolio_data': False,
                    'additionalInfo': {'query_understanding': query_info}
                }
            else:
                response = BingWebSearch.perform_bing_web_search(query_text=query, recency_importance=arguments['recency_importance'])
                # response = HybridSearchService.perform_hybrid_reranked_search(query_text=query, recency_importance=arguments['recency_importance'])
                response['additionalInfo']['query_understanding'] = query_info
        elif function_name == 'extract_portfolio_snapshot_details':
            aggregation_metric = arguments['aggregation_metric']
            aggregation_level = arguments['aggregation_level']
            companies_mentioned = arguments['companies_mentioned']
            sorting_order = arguments['sorting_order']
            response = {'searchArticleIds': [], 'additionalInfo': {'query_understanding': query_info},
                        'user_portfolio_data': True,
                        'portfolio_data': PortfolioService.get_current_portfolio_value(user_id=user_id, aggregation_level=aggregation_level, aggregation_metric=aggregation_metric,
                                                                                       companies_list=companies_mentioned, sorting_order=sorting_order)}
        elif function_name == 'extract_portfolio_growth_details':
            aggregation_metric = arguments['aggregation_metric']
            aggregation_level = arguments['aggregation_level']
            companies_mentioned = arguments['companies_mentioned']
            sorting_order = arguments['sorting_order']
            num_days = arguments['num_days']
            response = {'searchArticleIds': [], 'additionalInfo': {'query_understanding': query_info},
                        'user_portfolio_data': True,
                        'portfolio_data': PortfolioService.calc_growth_rate_for_user_portfolio_companies(user_id=user_id, aggregation_level=aggregation_level,
                                                                                                         aggregation_metric=aggregation_metric,
                                                                                                         companies_list=companies_mentioned, sorting_order=sorting_order,
                                                                                                         num_days=num_days)}
        elif function_name == 'get_share_price_history_for_companies':
            companies_mentioned = arguments['companies_mentioned']
            response = {'searchArticleIds': [], 'additionalInfo': {'query_understanding': query_info},
                        'user_portfolio_data': False,
                        'portfolio_data': PortfolioService.get_latest_share_price_trend_for_companies(companies_list=companies_mentioned)}
        return response
