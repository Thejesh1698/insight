import logging
import json
import pandas as pd
import psycopg2
import numpy as np
from datetime import datetime
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from typing import List, Union


class EmbeddingSQL:

    @staticmethod
    def get_model_name_in_emb_table() -> Union[str, None]:
        with PostgresDatabaseOperation() as cursor:
            sql = """
            SELECT DISTINCT model_name FROM embeddings
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            assert len(results) <= 1, f"more than 1 model_name found in embeddings table"
            if len(results) == 1:
                return results[0][0]
            else:
                return None

    @staticmethod
    def upsert_embeddings(article_id: str, embeddings: List[float], model_name: str, content_type: str = 'ARTICLE'):
        # cast numpy float into normal float

        # embeddings = [float(x) for x in embeddings]
        current_table_model_name = EmbeddingSQL.get_model_name_in_emb_table()
        if current_table_model_name:
            assert current_table_model_name == model_name, (f"provided model {model_name} is different from model used for other articles in table. "
                                                            f"Truncate table and regenerate for all articles if needed")

        # try:
        with PostgresDatabaseOperation() as cursor:
            # Parameterized query here
            upsert_sql_primary_table = """
            INSERT INTO embeddings (article_id, embedding, model_name, created_at, updated_at, content_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_id)
            DO UPDATE SET 
                embedding = EXCLUDED.embedding,
                model_name = EXCLUDED.model_name,
                updated_at = EXCLUDED.updated_at,
                content_type = EXCLUDED.content_type
                ;
            """
            # TODO: - harmonize the times
            current_time = datetime.now()
            cursor.execute(upsert_sql_primary_table, (article_id, embeddings, model_name, current_time, current_time, content_type))

            # upsert_sql_model_table = f"""
            #             INSERT INTO embeddings_{model_name} (article_id, embedding, created_at, updated_at)
            #             VALUES (%s, %s, %s, %s)
            #             ON CONFLICT (article_id)
            #             DO UPDATE SET
            #                 embedding = EXCLUDED.embedding,
            #                 updated_at = EXCLUDED.updated_at;
            #             """
            # current_time = datetime.now()
            # cursor.execute(upsert_sql_model_table, (article_id, embeddings, current_time, current_time))

    @staticmethod
    def get_embedding_and_model_name_for_article_id(article_id: str):

        with PostgresDatabaseOperation() as cursor:
            get_sql = "SELECT embedding, model_name FROM embeddings WHERE article_id = %s"
            cursor.execute(get_sql, (article_id,))
            result = cursor.fetchall()
            if len(result) > 0:
                emb = json.loads(result[0][0])
                model_name = result[0][1]
                emb = [float(x) for x in emb]
                return emb, model_name
            else:
                return None, None

    # TODO: - doesn't seem for this function to be in embedding SQL even though we are using that table
    @staticmethod
    def get_article_ids_with_embeddings() -> List[str]:
        with PostgresDatabaseOperation() as cursor:
            get_sql = "SELECT DISTINCT article_id FROM embeddings"
            cursor.execute(get_sql)
            result = cursor.fetchall()
            if len(result) > 0:
                return [row[0] for row in result]
            else:
                return []

    @staticmethod
    def get_all_embeddings() -> (dict, list):
        result = {}
        model_names = set()
        with PostgresDatabaseOperation() as cursor:
            get_sql = "SELECT article_id, embedding, model_name FROM embeddings"
            cursor.execute(get_sql)
            # result = cursor.fetchall()
            while True:
                batch = cursor.fetchmany(10000)
                if not batch:
                    break
                logging.info('new batch of embeddings fetched')
                for row in batch:
                    emb = json.loads(row[1])
                    result[row[0]] = [np.float16(emb[k]) for k in range(len(emb))]
                # result.append([(x[0], [np.float16(x[1][k]) for k in range(len(x[1]))]) for x in batch])
                cur_batch_models = set([x[2] for x in batch])
                model_names = model_names.union(cur_batch_models)
        # converting embeddings into float
        # logging.info('embeddings fetched successfully')
        # result = [(x[0], [np.float16(x[1][k]) for k in range(len(x[1]))], x[2]) for x in result]
        logging.info('embeddings list generated with float16')
        # df = pd.DataFrame(result, columns=['article_id', 'embedding', 'model_name'])
        return result, list(model_names)

    @staticmethod
    def get_all_relevant_embeddings() -> (dict, list):
        result = {}
        model_names = set()
        with PostgresDatabaseOperation() as cursor:
            get_sql = """SELECT DISTINCT e.article_id, embedding, e.model_name 
                         FROM embeddings e 
                         INNER JOIN llm_article_attributes laa
                         ON e.article_id = laa.article_id
                         WHERE laa.financial_news = True and laa.relevant_for_india = True
                         AND e.article_id NOT IN 
                         (SELECT DISTINCT article_id FROM manual_article_attributes WHERE financial_news = False or relevant_for_india = False)
                         """
            cursor.execute(get_sql)
            while True:
                batch = cursor.fetchmany(10000)
                if not batch:
                    break
                logging.info('new batch of embeddings fetched')
                for row in batch:
                    emb = json.loads(row[1])
                    result[row[0]] = [np.float16(emb[k]) for k in range(len(emb))]
                cur_batch_models = set([x[2] for x in batch])
                model_names = model_names.union(cur_batch_models)
        # converting embeddings into float
        logging.info('embeddings list generated with float16')
        return result, list(model_names)

    @staticmethod
    def get_category_embeddings(category: str) -> (dict, list):
        result = {}
        model_names = set()
        with PostgresDatabaseOperation() as cursor:
            get_sql = """SELECT DISTINCT e.article_id, embedding, e.model_name 
                             FROM embeddings e 
                             INNER JOIN llm_article_attributes laa
                             ON e.article_id = laa.article_id
                             WHERE laa.financial_news = True and laa.relevant_for_india = True
                             AND category = %s
                             AND e.article_id NOT IN 
                             (SELECT DISTINCT article_id FROM manual_article_attributes WHERE financial_news = False or relevant_for_india = False)
                             """
            cursor.execute(get_sql, (category,))
            while True:
                batch = cursor.fetchmany(10000)
                if not batch:
                    break
                logging.info('new batch of embeddings fetched')
                for row in batch:
                    emb = json.loads(row[1])
                    result[row[0]] = [np.float16(emb[k]) for k in range(len(emb))]
                cur_batch_models = set([x[2] for x in batch])
                model_names = model_names.union(cur_batch_models)
        # converting embeddings into float
        logging.info('embeddings list generated with float16')
        return result, list(model_names)





