from datetime import datetime
import logging
import pandas as pd
import numpy as np

from constants import ContentType, YT_SOURCE_ID
from sql.candidates.CandidateSQL import CandidateSQL
from sql.clustering.ClusteringSQL import ClusteringSQL
from src.articles.ArticleService import ArticleService
from src.candidates._utils import is_candidate, get_prior_for_popularity


class CandidatesService:

    def __init__(self):
        pass

    @staticmethod
    def calc_hours_since_publication(df):
        df['published_at'] = pd.to_datetime(df['published_at'])
        df['published_at'] = df['published_at'].apply(lambda x: x.replace(tzinfo=None))
        df['hours_since_publication'] = (datetime.today() - df['published_at']) / np.timedelta64(1, 'h')
        return df

    @staticmethod
    def get_llm_attributes():
        attributes_df = CandidateSQL.get_all_article_attributes()
        # if the validity is > 1 year or less than 0 (-1 being timeless), then set it to 365 days
        attributes_df['validity_duration'] = attributes_df['validity_duration'].apply(lambda x: 365 if x <= 0 or x >= 365 else x)
        attributes_df['validity_in_hours'] = attributes_df['validity_duration'] * 24
        attributes_dict = attributes_df.to_dict('records')
        for art_dict in attributes_dict:
            art_dict['prior_a'] = get_prior_for_popularity(article_attributes=art_dict)
        # expected_popularity_score_df = pd.DataFrame([('niche', 1), ('moderately_popular', 5), ('breaking_news', 15)], columns=['expected_popularity', 'prior_a'])
        # attributes_df = pd.merge(attributes_df, expected_popularity_score_df, how='inner', on='expected_popularity')
        attributes_df = pd.DataFrame(attributes_dict)
        # Default values
        return attributes_df

    @staticmethod
    def get_all_articles_metadata_from_api():
        clustered_article_ids = ClusteringSQL.get_article_ids_with_clusters()
        all_article_data = []
        # Fetch only articles which has image url and all podcasts
        valid_articles_metadata = ArticleService.get_all_Articles_metadata()
        for article_id in clustered_article_ids:
            if article_id in valid_articles_metadata:
                article_data = valid_articles_metadata[article_id]
                all_article_data.append((article_id, article_data.source_id, article_data.published_time, article_data.content_type))
                if article_data.content_type != 'article' and article_data.content_type != 'ARTICLE':
                    print(article_data)
        return pd.DataFrame(all_article_data, columns=['article_id', 'source_id', 'published_at', 'content_type'])

    @staticmethod
    def get_source_adjusted_validity_hours(row):
        timeless_eligible_sources = ['652d53256a2736f06f46cfcf', '65291b1e9a2fbc229e5f29c9', '6530d40d9a7559d3ec6b9871', '65558d1f672118037c541088']
        if row['content_type'] == ContentType.podcast_episode.value or row['source_id'] in timeless_eligible_sources:
            return row['validity_in_hours']
        else:
            timelimit = 336  # 2 weeks for non-timeless sources
            return min(row['validity_in_hours'], timelimit)

    @staticmethod
    def reduce_YT_representation(row):
        if row['source_id'] != YT_SOURCE_ID:
            return row['keep']
        else:
            return row['keep'] and np.random.rand() < 0.02

    @staticmethod
    def update_candidate_articles():
        logging.info(f'candidates: computation started at {datetime.now()}')
        all_articles_df = CandidatesService.get_all_articles_metadata_from_api()
        logging.info(f"candidates: fetched all articles metadata - for {len(all_articles_df)}")
        all_articles_df = CandidatesService.calc_hours_since_publication(df=all_articles_df)
        llm_attributes_df = CandidatesService.get_llm_attributes()
        logging.info(f"candidates: attributes found for {len(llm_attributes_df)} articles")
        all_articles_df = pd.merge(all_articles_df, llm_attributes_df, how='left', on='article_id')
        # If an article is not from an explicitly allowed timeless source, then remove it from candidates after a week for sure
        all_articles_df['validity_in_hours'] = all_articles_df.apply(lambda x: CandidatesService.get_source_adjusted_validity_hours(x), axis=1)
        all_articles_df['keep'] = [is_candidate(attributes_dict=attributes) for attributes in all_articles_df.to_dict('records')]
        # Hack to reduce the representation of YT news
        all_articles_df['keep'] = all_articles_df.apply(lambda x: CandidatesService.reduce_YT_representation(x), axis=1)
        candidates_df = all_articles_df[all_articles_df['keep'] == True][['article_id', 'published_at', 'source_id', 'prior_a', 'content_type']]
        logging.info(f'candidates: {len(candidates_df)} eligible candidates found')
        candidates_df = candidates_df.fillna({'prior_a': 1})
        candidates_df['prior_b'] = 10
        CandidateSQL.update_candidate_articles_in_db(candidates_df=candidates_df)
        logging.info(f'candidate updation complete at {datetime.now()}')
