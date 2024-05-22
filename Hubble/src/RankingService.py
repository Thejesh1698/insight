from datetime import datetime
import cohere
import numpy as np

from src.constants import timezone
from src._utils import compute_publication_decay_time
import pandas as pd
import os
from src.Article import Article
co = cohere.Client(os.environ.get('COHERE_KEY'))


class RankingService:

    @staticmethod
    def get_reranked_search_results(query_text, articles: [Article], max_published_date, num_results=100, recency_importance='Medium'):
        published_time_df = pd.DataFrame([(x.article_id, x.published_time) for x in articles], columns=['article_id', 'published_time'])
        relevance_scores_df = RankingService.perform_reranking(query_text=query_text, articles=articles, num_results=num_results)
        published_time_df = RankingService.format_published_time_df(published_time_df=published_time_df, max_published_date=max_published_date)
        # TODO: - this decay should be dynamic based on the timeliness of the query
        published_time_df['recency_score'] = [compute_publication_decay_time(x) for x in published_time_df['num_days_ago']]
        # recency_scores = RankingService.get_recency_scores(published_time_df=published_time_df)
        merged_scores_df = pd.merge(published_time_df, relevance_scores_df, how='left', on='article_id')
        recency_weight = 0.2
        if recency_importance.lower() == 'low':
            recency_weight = 0.1
        elif recency_importance.lower() == 'high':
            recency_weight = 0.3
        relevance_weight = 1 - recency_weight
        merged_scores_df['weighted_score'] = relevance_weight * merged_scores_df['relevance_score'] + recency_weight * merged_scores_df['recency_score']
        ranked_response = RankingService.get_ordered_response_object(merged_scores_df=merged_scores_df,
                                                                     num_results=num_results)
        return ranked_response

    @staticmethod
    def perform_reranking(query_text, articles: [Article], num_results=100):
        candidates = [{'article_id': x.article_id, 'text': x.full_content} for x in articles]
        d = datetime.now()
        response = co.rerank(
            model='rerank-english-v2.0',
            query=query_text,
            documents=candidates,
            top_n=num_results,
        )
        # print(f'fetched results from cohere in {datetime.now() - d} second')
        return pd.DataFrame([(x.document['article_id'], x.relevance_score) for x in response], columns=['article_id', 'relevance_score'])

    # @staticmethod
    # def get_reranked_search_results(similarity_df, published_time_df, num_results):
    #     published_time_df = RankingService.format_published_time_df(published_time_df=published_time_df)
    #     recency_scores = RankingService.get_recency_scores(published_time_df=published_time_df)
    #     similarity_scores = RankingService.get_modified_cosine_similarity(similarity_df=similarity_df)
    #     reranked_scores = RankingService.get_weighted_average_scores(similarity_scores=similarity_scores, recency_scores=recency_scores)
    #     ranked_response = RankingService.get_ordered_response_object(similarity_df=similarity_df,
    #                                                                  published_time_df=published_time_df,
    #                                                                  recency_scores=recency_scores,
    #                                                                  similarity_scores=similarity_scores,
    #                                                                  reranked_scores=reranked_scores,
    #                                                                  num_results=num_results)
    #     return ranked_response

    @staticmethod
    def get_reranked_scores(similarity_df):
        pass

    @staticmethod
    def format_published_time_df(published_time_df, max_published_date):
        published_time_df['published_time'] = pd.to_datetime(published_time_df['published_time'], utc=True)
        # today_reference = datetime.today().replace(tzinfo=timezone)
        today_reference=pd.to_datetime(max_published_date,utc=True)
        # published_time_df['num_days_ago'] = (today_reference - published_time_df['published_time']).dt.days
        published_time_df['num_days_ago'] = (today_reference - published_time_df['published_time']).dt.days
        return published_time_df

    @staticmethod
    def get_recency_scores(published_time_df):
        published_time_df['recency_score'] = [compute_publication_decay_time(n) for n in published_time_df['num_days_ago']]
        recency_scores = {row['article_id']: row['recency_score'] for i, row in published_time_df.iterrows()}
        return recency_scores

    @staticmethod
    def get_modified_cosine_similarity(similarity_df):
        max_cosine_similarity = similarity_df['cosine_similarity'].max()
        assert max_cosine_similarity > 0, f"the max cosine similarity is not > 0 and is {max_cosine_similarity}"
        similarity_df['corrected_similarity'] = similarity_df['cosine_similarity'] / max_cosine_similarity
        return {row['article_id']: row['corrected_similarity'] for i, row in similarity_df.iterrows()}

    @staticmethod
    def get_weighted_average_scores(similarity_scores, recency_scores):
        similarity_weight = 2
        recency_weight = 1
        total_weight = similarity_weight + recency_weight
        weighted_scores = {x: (similarity_weight * similarity_scores[x] + recency_weight * recency_scores[x]) / total_weight for x in similarity_scores.keys()}
        return weighted_scores

    @staticmethod
    def get_ordered_response_object(merged_scores_df, num_results):
        # Sorting article_ids based on reranked_scores
        merged_scores_df = merged_scores_df.nlargest(num_results, columns='weighted_score')
        results_dict = merged_scores_df.to_dict('records')
        sorted_article_ids = [{'article_id': x['article_id']} for x in results_dict]
        additional_info = {}
        for article_info in results_dict:
            aid = article_info.pop('article_id')
            additional_info[aid] = article_info
        # Combining everything into the final dictionary
        final_dict = {
            'searchArticleIds': sorted_article_ids,
            'additionalInfo': additional_info
        }

        return final_dict
