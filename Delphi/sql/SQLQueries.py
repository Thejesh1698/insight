from typing import List
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation


def get_article_ids_with_embeddings() -> List[str]:
    with PostgresDatabaseOperation() as cursor:
        get_sql = "SELECT DISTINCT article_id FROM embeddings"
        cursor.execute(get_sql)
        result = cursor.fetchall()
        if len(result) > 0:
            return [row[0] for row in result]
        else:
            return []