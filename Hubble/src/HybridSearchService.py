import time

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import os
import json
import logging
from sql.SearchSQL import SearchSQL
from src.ArticleService import ArticleService
from src.EmbeddingsService import EmbeddingsService
from datetime import datetime, timedelta
from src.constants import INDIAN_SOURCES
from src.RankingService import RankingService
from src._utils import compute_publication_decay_time, create_recency_score_df, calc_recency_weighted_relevance

# logger = logging.getLogger('__name__')
logger = logging.getLogger()
level = logging.CRITICAL
logger.setLevel(level)

ES_URL = f'https://{os.environ.get("ES_HOST")}/finance-content/_search'
embedding_service = EmbeddingsService(hf_model_path='BAAI/bge-large-en-v1.5')


class HybridSearchService:

    @staticmethod
    def _perform_exact_search(query_text, recency_importance, max_published_date, n=100):
        headers = {"Content-Type": "application/json"}
        query = {
            "size": n,
            "query": {
                "bool": {
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    {"match": {"title": query_text}},
                                    {"match": {"short_description": query_text}},
                                    {"match": {"cleaned_text": query_text}}
                                ],
                                "minimum_should_match": 1
                            }
                        },
                        {"term": {"is_premium_article": False}},
                        {"match": {"content_type": "ARTICLE"}},
                        # {"terms": {"source_id": INDIAN_SOURCES}}
                    ]
                }
            },
            "_source": False,
            "script_fields": {
                "doc_id": {
                    "script": {
                        "lang": "painless",
                        "source": "doc['_id']"
                    }
                }
            }
        }

        # Dynamically add range query based on min_published_date and max_published_date
        range_filter = {}
        # Parse the date string into a datetime object
        if max_published_date:
            max_date = datetime.strptime(max_published_date, '%Y-%m-%dT%H:%M:%S')
            min_published_date = None
            if recency_importance == 'high':
                min_published_date = (max_date - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S')
            if min_published_date is not None:
                range_filter["gte"] = min_published_date
            if max_published_date is not None:
                range_filter["lt"] = max_published_date
            # Only add the range query if either date is provided
            if range_filter:
                query["query"]["bool"]["must"].append({
                    "range": {
                        "published_time": range_filter
                    }
                })

        response = requests.get(ES_URL, auth=HTTPBasicAuth(username=os.environ.get('ES_USERNAME'), password=os.environ.get('ES_PASSWORD')), headers=headers, json=query)
        results = json.loads(response.text)['hits']['hits'][:n]
        return pd.DataFrame([(x['_id'], x['_score']) for x in results], columns=['article_id', 'score'])

    @staticmethod
    def _perform_semantic_search(query_text, n=100):
        start_time = time.time()
        query_embeddings = SearchSQL.get_query_text_embeddings(query=query_text)
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to try and retrieve embeddings for search query {query_text}")
        if not query_embeddings:
            query_embeddings = embedding_service.extract_embeddings_for_text(content=query_text)
            # logger.info(f"took {round(time.time() - start_time, 3)} seconds to generate query embeddings for search query {query_text}")
            SearchSQL.save_embedding_for_query_text(query_text=query_text, emb=query_embeddings)
            # logger.info(f"took {round(time.time() - start_time, 3)} seconds to save query embeddings for search query {query_text}")
        top_similarity_articles_df = SearchSQL.get_n_closest_articles_for_embedding(emb=query_embeddings, n=n)
        return top_similarity_articles_df

    @staticmethod
    def perform_hybrid_reranked_search(query_text, recency_importance='medium', max_published_date=None, search_n=250, return_n=100):
        start_time = time.time()
        if not max_published_date:
            max_published_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%S')
        if recency_importance not in ['low', 'Low', 'high', 'High']:
            recency_importance = 'medium'
        semantic_article_df = HybridSearchService._perform_semantic_search(query_text, n=search_n)
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to retrieve nearest {search_n} sematic items for search query {query_text}")
        exact_article_df = HybridSearchService._perform_exact_search(query_text, recency_importance=recency_importance, max_published_date=max_published_date, n=search_n)
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to retrieve nearest {search_n} exact items for search query {query_text}")
        top_article_ids = set(list(semantic_article_df['article_id'].unique())).union(set(list(exact_article_df['article_id'].unique())))
        articles_dict = ArticleService.get_Articles_from_list(top_article_ids, max_published_date=max_published_date,indian_sources_only=True)
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to fetch the metadata from mongo for search query {query_text}")
        all_articles = list(articles_dict.values())
        recency_scores_df = create_recency_score_df(articles=all_articles, max_published_date=max_published_date)
        if not semantic_article_df.empty:
            weighted_sematic = calc_recency_weighted_relevance(relevance_df=semantic_article_df, recency_df=recency_scores_df, recency_importance=recency_importance, return_n=return_n)
            top_recent_sematic_articles = list(weighted_sematic['article_id'].unique())
        else:
            logger.warning(f'empty sematic results for {query_text}')
            top_recent_sematic_articles = []
        if not exact_article_df.empty:
            weighted_exact = calc_recency_weighted_relevance(relevance_df=exact_article_df, recency_df=recency_scores_df, recency_importance=recency_importance, return_n=return_n)
            top_recent_exact_articles = list(weighted_exact['article_id'].unique())
        else:
            logger.warning(f'empty exact results for {query_text}')
            top_recent_exact_articles = []
        top_recent_articles = [article for article_id, article in articles_dict.items() if (article_id in top_recent_exact_articles + top_recent_sematic_articles) and article.full_content is not None]
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to calculate recency weighted items {query_text}")
        if not top_recent_articles:
            return {
            'searchArticleIds': [],
            'additionalInfo': {}
        }
        search_response_object = RankingService.get_reranked_search_results(query_text=query_text, articles=top_recent_articles, num_results=return_n,
                                                                            max_published_date=max_published_date, recency_importance=recency_importance)
        # logger.info(f"took {round(time.time() - start_time, 3)} seconds to rerank the results for search query {query_text}")
        return search_response_object
