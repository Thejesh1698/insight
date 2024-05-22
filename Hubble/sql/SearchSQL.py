from datetime import datetime
from typing import List, Union
import json
import os
import pandas as pd
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation


class SearchSQL:

    @staticmethod
    def get_query_text_embeddings(query: str) -> Union[List, None]:
        with PostgresDatabaseOperation() as cursor:
            sql = 'SELECT embedding FROM search_query_embeddings WHERE query_text = %s LIMIT 1'
            cursor.execute(sql, (query,))
            results = cursor.fetchall()
        if results:
            return json.loads(results[0][0])
        else:
            return None

    @staticmethod
    def get_n_closest_articles_for_embedding(emb: List, n: int):
        # SET LOCAL ivfflat.probes = 10;
        with PostgresDatabaseOperation() as cursor:
            sql = """
            SET hnsw.ef_search = %s;
            SELECT article_id, 
                       1- (embedding <=> %s) AS cosine_sim
                FROM embeddings
                ORDER BY embedding <=> %s
                LIMIT %s;
            """
            cursor.execute(sql, (n, str(emb), str(emb), n))
            results = cursor.fetchall()
        return pd.DataFrame(results, columns=['article_id', 'score'])

    @staticmethod
    def save_embedding_for_query_text(query_text: str, emb: List):
        with PostgresDatabaseOperation() as cursor:
            sql = """
            INSERT INTO search_query_embeddings (query_text, embedding, model_name, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (query_text, model_name)
            DO UPDATE SET
            embedding = EXCLUDED.embedding
            """
            cursor.execute(sql, (query_text, emb, os.environ.get('EMBEDDING_MODEL_NAME'), datetime.now()))
