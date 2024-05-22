import logging
import os

import pandas as pd
import psycopg2
from datetime import datetime

from constants import ContentType
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from typing import List, Union


class CandidateSQL:

    def __init__(self):
        pass

    @staticmethod
    def get_day_wise_article_a_b() -> pd.DataFrame:
        # TODO: - to evaluate if we need to take count distinct for feed id in case articles can duplicate
        # TODO: - do this only for candidate articles
        with PostgresDatabaseOperation() as cursor:
            interaction_sql = f"""SELECT article_id, CAST(created_at AS DATE) as feed_date, SUM(CAST(is_article_opened AS INT)) as a, COUNT(activity_id) as b
                                   FROM user_article_interactions
                                   GROUP BY article_id, feed_date 
                                   """
            cursor.execute(interaction_sql)
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['article_id', 'feed_date', 'a', 'b'])
            return df

    @staticmethod
    def add_article_to_candidates_without_priors(article_id, published_at, source_id):
        with PostgresDatabaseOperation() as cursor:
            insert_sql = """
                INSERT INTO candidate_articles (article_id, published_at, source_id)
                VALUES (%s, %s, %s)
                ON CONFLICT (article_id) DO NOTHING;
                """
            cursor.execute(insert_sql, (article_id, published_at, source_id))

    @staticmethod
    def add_article_to_candidates_with_priors(article_id, published_at, source_id, prior_a, prior_b, content_type=ContentType.article.value):
        with PostgresDatabaseOperation() as cursor:
            insert_sql = """
                    INSERT INTO candidate_articles (article_id, published_at, source_id, prior_a, prior_b, content_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (article_id)
                    DO UPDATE SET
                        prior_a = EXCLUDED.prior_a,
                        prior_b = EXCLUDED.prior_b,
                        content_type = EXCLUDED.content_type
                    """
            cursor.execute(insert_sql, (article_id, published_at, source_id, prior_a, prior_b, content_type))

    @staticmethod
    def update_candidate_article_with_prior(article_id, prior_a, prior_b):
        with PostgresDatabaseOperation() as cursor:
            insert_sql = """
                    UPDATE candidate_articles
                    SET 
                        prior_a = %s,
                        prior_b = %s
                    WHERE article_id = %s
                    """
            cursor.execute(insert_sql, (prior_a, prior_b, article_id))

    @staticmethod
    def remove_article_from_candidates(article_id):
        with PostgresDatabaseOperation() as cursor:
            delete_sql = f"""
            DELETE FROM candidate_articles
            WHERE article_id = %s
            """
            cursor.execute(delete_sql, (article_id,))
            logging.info(f'removed {article_id} from candidates')

    @staticmethod
    def get_all_article_attributes():
        with PostgresDatabaseOperation() as cursor:
            sql = """
                    SELECT A.article_id, financial_news, relevant_for_india, validity_duration, expected_popularity,  interest_score, headline_score, novelty_score, emotional_score
                    FROM llm_article_attributes A
                    INNER JOIN (
                        SELECT article_id, MAX(updated_at) as max_updated_at
                        FROM llm_article_attributes
                        GROUP BY article_id
                    ) AS B ON A.article_id = B.article_id AND A.updated_at = B.max_updated_at;
                    """
            cursor.execute(sql)
            result = cursor.fetchall()
        df = pd.DataFrame(result, columns=['article_id', 'financial_news', 'relevant_for_india', 'validity_duration', 'expected_popularity', 'final_reader_interest_score',
                                           'final_headline_effectiveness_score', 'final_event_novelty_score', 'final_emotional_impact_score'])
        return df

    @staticmethod
    def get_source_id_characteristics():
        with PostgresDatabaseOperation() as cursor:
            sql = """
                        SELECT source_id, publication_date_decay
                        FROM source_id_characteristics
                        """
            cursor.execute(sql)
            result = cursor.fetchall()
        df = pd.DataFrame(result, columns=['source_id', 'publication_date_decay'])
        return df

    @staticmethod
    def get_all_candidate_article_ids():
        with PostgresDatabaseOperation() as cursor:
            sql = """
            SELECT DISTINCT article_id FROM candidate_articles
            """
            cursor.execute(sql)
            results = cursor.fetchall()
        return [x[0] for x in results]

    @staticmethod
    def update_candidate_articles_in_db(candidates_df):
        with PostgresDatabaseOperation() as cursor:
            truncate_sql = """TRUNCATE TABLE candidate_articles"""
            cursor.execute(truncate_sql)

            insert_sql = """
                INSERT INTO candidate_articles (article_id, published_at, source_id, prior_a, prior_b, content_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
            for index, row in candidates_df.iterrows():
                cursor.execute(insert_sql, (row['article_id'], row['published_at'], row['source_id'], row['prior_a'], row['prior_b'], row['content_type']))

    @staticmethod
    def update_candidate_articles_in_db_old(candidates_df):
        with PostgresDatabaseOperation() as cursor:
            truncate_sql = """TRUNCATE TABLE candidate_articles"""
            cursor.execute(truncate_sql)

            insert_sql = """
            INSERT INTO candidate_articles (article_id, published_at, source_id)
            VALUES (%s, %s, %s)
            """
            for index, row in candidates_df.iterrows():
                cursor.execute(insert_sql, (row['article_id'], row['published_at'], row['source_id']))

    @staticmethod
    def add_new_source_details(source_id, source_name, publication_date_decay):
        with PostgresDatabaseOperation() as cursor:
            insert_sql = """
            INSERT INTO source_id_characteristics (source_id, publication_date_decay, source_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (source_id)
            DO UPDATE SET
                publication_date_decay = EXCLUDED.publication_date_decay,
                source_name = EXCLUDED.source_name
            """
            cursor.execute(insert_sql, (source_id, publication_date_decay, source_name))
