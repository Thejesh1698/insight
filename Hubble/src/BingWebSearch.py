import time

import requests
from newspaper import Article, Config
import concurrent.futures
import datetime
import tldextract
import os
import logging
import numpy as np
import json
from src.constants import BACKEND_URL
logger = logging.getLogger()
level = logging.INFO
logger.setLevel(level)


class BingWebSearch:
    MAX_THREADS = 10
    COUNT = 10
    FRESHNESS = "Month"
    BING_API_KEY = os.environ.get('BING_API_KEY')

    LINKS_TO_EXCLUDE = [
        "-site:youtube.com",
        "-site:amazon.com",
        "-site:hotstar.com",
        "-site:netflix.com",
        "-site:primevideo.com",
        "-site:sonyliv.com",
        "-site:zee5.com",
        "-site:voot.com",
        "-site:spotify.com",
        "-site:bing.com/videos"
    ]

    sources_mapping = {
        "indiatimes": "economic-times",
        "zerodha": "zerodha-varsity",
        "ndtvprofit": "ndtv-profit",
        "businessworld": "business-world",
        "businessinsider": "business-standard",
        "yahoo": "yahoo-finance",
        "moneycontrol": "money-control",
        "cnbctv18": "cnbc-tv-18",
        "livemint": "live-mint",
        "wintwealth": "wint-wealth",
        "youtu": "you-tube",
        "youtube": "you-tube"
    }

    @staticmethod
    def _search_and_clean_articles_bing(user_query, recency_importance='medium'):

        urls = BingWebSearch._get_urls(user_query, recency_importance=recency_importance)
        start_time = datetime.datetime.now()
        results = {"articles": []}
        results_idx_dict = {}
        if urls:
            with concurrent.futures.ThreadPoolExecutor(max_workers=BingWebSearch.MAX_THREADS) as executor:
                futures = [executor.submit(BingWebSearch._parse_article, url, idx) for idx, url in enumerate(urls)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        article_dict, result_idx = future.result()
                        if article_dict:
                            article_dict = BingWebSearch.clean_article_dict_data(article_dict)
                            if BingWebSearch.is_article_dict_valid(article_dict):
                                # if 'url' in article_dict and 'source' in article_dict:
                                results_idx_dict[result_idx] = article_dict
                    except Exception as e:
                        logger.info(f"Error occurred while parsing: {e}")
            end_time = datetime.datetime.now()
            print(f"Time taken to Complete Parsing all Articles Excluding Bing Search: {(end_time - start_time).total_seconds()} seconds")
        else:
            print("No URLs found in the search results.")
        valid_extracted_indices = list(np.sort(list(results_idx_dict.keys())))
        for cur_idx in valid_extracted_indices:
            results['articles'].append(results_idx_dict[cur_idx])
        return results

    @staticmethod
    def is_article_dict_valid(article_dict):
        title_cleaned_text_exists = all(article_dict.get(key) not in (None, "None", "") for key in ["cleanedText", "title"])  # title and cleaned text are mandatory
        cleaned_text_valid = len(article_dict['cleanedText']) >= 300
        valid_url_source = ('url' in article_dict) and ('source' in article_dict)
        return cleaned_text_valid and title_cleaned_text_exists and valid_url_source

    @staticmethod
    def clean_article_dict_data(article_dict):
        source_name = tldextract.extract(article_dict["url"]).domain
        article_dict["source"] = BingWebSearch.sources_mapping.get(source_name, source_name)
        extracted = tldextract.extract(article_dict["url"])
        logo_url = article_dict["sourceLogoURL"]
        if logo_url.startswith("/"):
            article_dict["sourceLogoURL"] = f"{extracted.domain}.{extracted.suffix}{logo_url}"
        return article_dict

    @staticmethod
    def perform_bing_web_search(query_text, recency_importance='medium'):
        start_time = time.time()
        article_results = BingWebSearch._search_and_clean_articles_bing(user_query=query_text, recency_importance=recency_importance)
        print(f'articles fetched from bing and cleaned for {query_text} in {time.time() - start_time} secs')
        start_time = time.time()
        article_ids = BingWebSearch._create_articles_in_backend(article_results=article_results)
        print(f'articles created in the backend for {query_text} in {time.time() - start_time} secs')
        response_article_ids = [{"article_id": x} for x in article_ids]
        # response_dict = {
        #     "searchArticleIds": response_article_ids,
        #     "additionalInfo": {'bing_query_details': {'search_source': 'bing', 'freshness': BingWebSearch.FRESHNESS}}
        # }
        response_dict = {
            "searchArticleIds": response_article_ids,
            "additionalInfo": {}
        }
        return response_dict

    @staticmethod
    def _create_articles_in_backend(article_results):
        url = f"{BACKEND_URL}/cloud/articles/register-search-articles"
        response = requests.post(url, json=article_results)
        if response.status_code == 200:
            data = response.json()
            article_ids = data.get("articleIds", [])
            return article_ids
        else:
            logger.info("Failed to get articleIds:", response.text)
            return []

    @staticmethod
    def _parse_article(url, result_index):
        def convert_valid_date_to_str(dt):
            if dt:
                formatted_dt = dt.strftime('%Y-%m-%dT%H:%M:%S')

                # Add timezone if it exists
                if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
                    tz_str = dt.strftime('%z')
                    formatted_dt += tz_str[:-2] + ':' + tz_str[-2:]

                return formatted_dt
            else:
                return None

        config = Config()
        config.fetch_images = False
        config.request_timeout = 1.5
        start_time = datetime.datetime.now()
        try:
            article = Article(url, config=config)
            article.download()
            is_premium = article.parse()
            if not is_premium:
                end_time = datetime.datetime.now()
                print("URL:", article.url)
                url = article.url,
                parsed_published_time = convert_valid_date_to_str(article.publish_date)
                article_dict = {
                    "url": article.url,
                    "source": "",
                    "sourceLogoURL": article.meta_favicon,
                    "title": article.title,
                    "shortDescription": article.meta_description,
                    "publishedTime": parsed_published_time,
                    "tags": list(article.tags),
                    "articleImage": article.top_image,
                    "Authors": list(article.authors),
                    "cleanedText": article.text
                }
                cleaned_dict = {}
                for k, v in article_dict.items():
                    if v:
                        cleaned_dict[k] = v
                print("Time taken to parse an Article:", (end_time - start_time).total_seconds(), "seconds")
                return cleaned_dict, result_index
            else:
                print("Premium Article Found", url)
                return None, None
        except Exception as e:
            print(f" Skipped Timeout URL", url)
            return None, None

    @staticmethod
    def _get_urls(user_query, recency_importance='medium'):
        headers = {
            'Ocp-Apim-Subscription-Key': BingWebSearch.BING_API_KEY,
            'Location': 'India'
        }

        response_filter = ["Webpages", "News"]
        params = {
            "mkt": "en-IN",
            "responseFilter": response_filter,
            "count": BingWebSearch.COUNT
        }
        if recency_importance == 'high':
            params["freshness"] = BingWebSearch.FRESHNESS
        url = "https://api.bing.microsoft.com/v7.0/search"
        params["q"] = user_query + " " + " ".join(BingWebSearch.LINKS_TO_EXCLUDE)
        response = requests.get(url, params=params, headers=headers)

        search_results = response.json()
        urls = []
        if 'webPages' in search_results and 'value' in search_results['webPages']:
            urls = [result['url'] for result in search_results['webPages']['value']]
        print(f'fetched the urls {urls} for the query {user_query}')
        return urls
