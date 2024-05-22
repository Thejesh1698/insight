import psycopg2
from datetime import datetime
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from typing import List, Dict
import pandas as pd


# TODO: - function to truncate table whenever new clusters are formed
# TODO: - get preferences for a single topic id in a dict
class TopicPreferencesSQL:

    @staticmethod
    def get_all_topic_preferences_from_db() -> pd.DataFrame:
        with PostgresDatabaseOperation() as cursor:
            sql = "SELECT topic_id, topic_name, cluster_id, a, b, clustering_run_id, created_at FROM topic_cluster_preference_mapping"
            cursor.execute(sql)
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['topic_id', 'topic_name', 'cluster_id', 'a', 'b', 'clustering_run_id', 'created_at'])

        return df

    @staticmethod
    def reset_all_topic_preferences_in_db():
        with PostgresDatabaseOperation() as cursor:
            sql = "TRUNCATE TABLE topic_cluster_preference_mapping"
            cursor.execute(sql)

    @staticmethod
    def save_topic_preferences_to_db(topic_id: int, topic_name: str, topic_cluster_preferences: Dict[int, Dict[str, float]], clustering_run_id: str):
        # validations about input params
        assert isinstance(topic_id, int), f"topic_id {topic_id} is not int"
        for cluster in topic_cluster_preferences:
            assert 'a' in topic_cluster_preferences[cluster] and 'b' in topic_cluster_preferences[cluster], f"Both 'a' and 'b' must be present in for cluster {cluster}."

        # validations if data already present in db
        current_preferences = TopicPreferencesSQL.get_all_topic_preferences_from_db()
        if not current_preferences.empty:
            assert topic_id not in current_preferences['topic_id'].unique(), f"topic {topic_id} already present in preferences table"
            assert clustering_run_id == current_preferences['clustering_run_id'].unique()[0], f"clustering run id {clustering_run_id} not same as one already in table"

        with PostgresDatabaseOperation() as cursor:
            insert_sql = f"""INSERT INTO topic_cluster_preference_mapping (topic_id, topic_name, cluster_id, a, b, clustering_run_id, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                          """
            current_time = datetime.now()
            for cluster_id in topic_cluster_preferences.keys():
                a = topic_cluster_preferences[cluster_id]['a']
                b = topic_cluster_preferences[cluster_id]['b']
                cursor.execute(insert_sql, (topic_id, topic_name, cluster_id, a, b, clustering_run_id, current_time))






