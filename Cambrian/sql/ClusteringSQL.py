from datetime import datetime
import pandas as pd
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
import json


class ClusteringSQL:

    # TODO: - add support for taking custom run_id
    @staticmethod
    def get_story_to_cluster_mapping() -> dict:
        """
        gets the latest storyline to cluster mapping
        :return: dictionary of storyline to cluster
        """
        with PostgresDatabaseOperation() as cursor:
            sql = """
            SELECT storyline_id, cluster_id, clustering_run_id FROM storyline_to_cluster_mapping
            """
            cursor.execute(sql)
            result = cursor.fetchall()

            df = pd.DataFrame(result, columns=['storyline_id', 'cluster_id', 'clustering_run_id'])
            assert df['clustering_run_id'].nunique() == 1, f"mapping not from unique cluster run, {df['clustering_run_id'].nunique()} run ids found"
            story_to_cluster_mapping = {}
            for mapping in result:
                story_to_cluster_mapping[mapping[0]] = mapping[1]

        return story_to_cluster_mapping

    @staticmethod
    def get_cluster_names():
        with PostgresDatabaseOperation() as cursor:
            run_id_sql = "SELECT DISTINCT parent_id, parent_name FROM cluster_hierarchy"
            cursor.execute(run_id_sql)

            result = cursor.fetchall()

        all_cluster_names = {}
        for cluster in result:
            all_cluster_names[cluster[0]] = cluster[1]
        return all_cluster_names

    @staticmethod
    def get_storyline_cluster_ids_for_article_id_list(article_ids):
        with PostgresDatabaseOperation() as cursor:
            sql = """SELECT article_id, storyline_id, cluster_id FROM article_to_cluster_mapping WHERE article_id in %s"""
            cursor.execute(sql, (tuple(article_ids),))
            results = cursor.fetchall()
        map_df = pd.DataFrame(results, columns=['article_id', 'storyline_id', 'cluster_id'])
        return {row['article_id']: {'storyline_id': row['storyline_id'], 'cluster_id': row['cluster_id']} for index, row in map_df.iterrows()}
