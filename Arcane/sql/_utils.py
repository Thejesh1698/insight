from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from typing import List


def remove_article_ids_from_ml_db(article_ids: List[str]):
    with PostgresDatabaseOperation() as cursor:
        delete_embeddings = 'DELETE FROM embeddings WHERE article_id IN %s'
        cursor.execute(delete_embeddings, (tuple(article_ids),))

        delete_candidates = 'DELETE FROM candidate_articles WHERE article_id IN %s'
        cursor.execute(delete_candidates, (tuple(article_ids),))

        delete_cluster_mapping = 'DELETE FROM article_to_cluster_mapping WHERE article_id IN %s'
        cursor.execute(delete_cluster_mapping, (tuple(article_ids),))

