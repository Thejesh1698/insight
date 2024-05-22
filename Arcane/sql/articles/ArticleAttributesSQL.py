import os

import pandas as pd
import psycopg2
from datetime import datetime
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from sql.MongoDatabaseConnection import MongoDatabaseConnection
from typing import List, Union


class ArticleAttributesSQL:

    def __init__(self):
        pass

    @staticmethod
    def save_article_attributes(article_id, article_attributes, finetune_id):
        # Validation of dict
        assert isinstance(article_attributes, dict)
        assert 'financial_or_business_news' in article_attributes
        assert isinstance(article_attributes['financial_or_business_news'], bool)
        assert 'relevant_for_india' in article_attributes
        assert isinstance(article_attributes['relevant_for_india'], bool)
        assert 'article_validity_duration' in article_attributes
        assert isinstance(article_attributes['article_validity_duration'], int)
        assert 'popularity' in article_attributes
        assert isinstance(article_attributes['popularity'], str)
        assert 'article_type' in article_attributes
        assert isinstance(article_attributes['article_type'], str)
        assert 'article_sentiment' in article_attributes
        assert isinstance(article_attributes['article_sentiment'], str)

        with PostgresDatabaseOperation() as cursor:
            insert_sql = """
                            INSERT INTO llm_article_attributes 
                            (article_id, financial_news, relevant_for_india, validity_duration, expected_popularity, article_type, sentiment, 
                            model_finetune_id, interest_score, headline_score, novelty_score, emotional_score, india_flag, category, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (article_id, model_finetune_id)
                            DO UPDATE SET
                                financial_news = EXCLUDED.financial_news,
                                relevant_for_india = EXCLUDED.relevant_for_india,
                                validity_duration = EXCLUDED.validity_duration,
                                expected_popularity = EXCLUDED.expected_popularity,
                                article_type = EXCLUDED.article_type,
                                sentiment = EXCLUDED.sentiment,
                                interest_score = EXCLUDED.interest_score,
                                headline_score = EXCLUDED.headline_score,
                                novelty_score = EXCLUDED.novelty_score,
                                emotional_score = EXCLUDED.emotional_score,
                                india_flag = EXCLUDED.india_flag,
                                category = EXCLUDED.category,
                                updated_at = EXCLUDED.updated_at
                            """
            cursor.execute(insert_sql, (article_id,
                                        article_attributes['financial_or_business_news'],
                                        article_attributes['relevant_for_indians'],
                                        article_attributes['article_validity_duration'],
                                        article_attributes['popularity'],
                                        article_attributes['article_type'],
                                        article_attributes['article_sentiment'],
                                        finetune_id,
                                        article_attributes['final_reader_interest_score'],
                                        article_attributes['final_headline_effectiveness_score'],
                                        article_attributes['final_event_novelty_score'],
                                        article_attributes['final_emotional_impact_score'],
                                        article_attributes['indian_or_international'],
                                        article_attributes['category'],
                                        datetime.now()
                                        ))

    @staticmethod
    def get_attributes_for_article_id(article_id):
        # get the latest created attributes for the article (model agnostic)
        with PostgresDatabaseOperation() as cursor:
            sql = f'''
            SELECT article_id, financial_news, relevant_for_india, validity_duration, expected_popularity
            FROM llm_article_attributes
            WHERE article_id = %s
            ORDER BY created_at DESC LIMIT 1
            '''
            cursor.execute(sql, (article_id,))
            results = cursor.fetchall()
        if results:
            results = results[0]
            return {results[0]: {'financial_news': results[1], 'relevant_for_india': results[2], 'validity_duration': results[3], 'expected_popularity': results[4]}}
        else:
            return {}




