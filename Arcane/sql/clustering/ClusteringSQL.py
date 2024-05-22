from datetime import datetime
import pandas as pd
import psycopg2
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
import json
from typing import Union, List


class ClusteringSQL:
    # TODO: - move all truncations to temp table approach and centralize that approach
    @staticmethod
    def insert_clustering_run_details(clustering_run_id: str, clustering_run_config: dict):
        with PostgresDatabaseOperation() as cursor:
            upsert_sql_primary_table = """
            INSERT INTO clustering_runs (clustering_run_id, config, created_at)
            VALUES (%s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(upsert_sql_primary_table, (clustering_run_id, json.dumps(clustering_run_config), current_time))

    @staticmethod
    def insert_cluster_hierarchy(cluster_hierarchy_df: pd.DataFrame, clustering_run_id: str):
        # TODO: - move to temp table approach.
        # TODO: - check if that temp table approach can be abstracted out
        expected_columns = ['parent_id', 'parent_name', 'child_storyline_list', 'child_left_id', 'child_left_name', 'child_right_id', 'child_right_name']
        assert set(expected_columns).issubset(set(cluster_hierarchy_df.columns)), f"some columns missing from {cluster_hierarchy_df.columns}"

        with PostgresDatabaseOperation() as cursor:
            # first truncate the data in live table
            truncate_sql = f"""
                    TRUNCATE TABLE cluster_hierarchy RESTART IDENTITY
            """
            cursor.execute(truncate_sql)

            # Insert the data in live and history tables
            insert_sql = f"""
                INSERT INTO cluster_hierarchy (parent_id, parent_name, child_storyline_list, child_left_id, child_left_name, child_right_id, child_right_name, clustering_run_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            history_sql = f"""
                INSERT INTO cluster_hierarchy_history (parent_id, parent_name, child_storyline_list, child_left_id, child_left_name, child_right_id, child_right_name, clustering_run_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            current_time = datetime.now()
            for index, row in cluster_hierarchy_df.iterrows():
                cursor.execute(insert_sql, (row['parent_id'], row['parent_name'], row['child_storyline_list'], row['child_left_id'], row['child_left_name'],
                                            row['child_right_id'], row['child_right_name'], clustering_run_id, current_time))
                cursor.execute(history_sql, (row['parent_id'], row['parent_name'], row['child_storyline_list'], row['child_left_id'], row['child_left_name'],
                                             row['child_right_id'], row['child_right_name'], clustering_run_id, current_time))

            # self.connection.commit()
            # cursor.close()

    @staticmethod
    def save_article_to_cluster_mapping(article_id_to_storyline_mapping: dict, article_id_to_cluster_mapping: dict, clustering_run_id: str):
        with PostgresDatabaseOperation() as cursor:
            truncate_sql = f"""TRUNCATE TABLE article_to_cluster_mapping RESTART IDENTITY
                                """
            cursor.execute(truncate_sql)

            insert_sql = f"""INSERT INTO article_to_cluster_mapping (article_id, storyline_id, cluster_id, clustering_run_id, created_at)
                                 VALUES (%s, %s, %s, %s, %s)
                              """
            current_time = datetime.now()
            for article_id in article_id_to_storyline_mapping.keys():
                cursor.execute(insert_sql,
                               (article_id, int(article_id_to_storyline_mapping[article_id]), int(article_id_to_cluster_mapping[article_id]), clustering_run_id, current_time))

    @staticmethod
    def save_article_story_cluster_mapping(article_story_cluster_mapping: dict, clustering_run_id: str):
        def chunked_data(data, size):
            """Yield successive chunk_size-sized chunks from data."""
            for i in range(0, len(data), size):
                yield data[i:i + size]

        with PostgresDatabaseOperation() as cursor:
            # Create a temporary table
            cursor.execute("CREATE TABLE temp_article_to_cluster_mapping (LIKE article_to_cluster_mapping INCLUDING ALL)")

            # Prepare data for bulk insert
            bulk_data = []
            for article_id, article_dict in article_story_cluster_mapping.items():
                bulk_data.append((
                    article_id,
                    int(article_dict['storyline_id']),
                    int(article_dict['cluster_id']),
                    clustering_run_id,
                    float(article_dict['storyline_prob']),
                    int(article_dict['story_cluster_id']),
                    int(article_dict['max_agg_cluster_id']),
                    float(article_dict['agg_cluster_prob'])
                ))

            # Bulk insert in chunks
            insert_sql = f"""INSERT INTO temp_article_to_cluster_mapping 
                             (article_id, storyline_id, cluster_id, clustering_run_id, storyline_prob, story_cluster_id, max_agg_cluster_id, agg_cluster_prob)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                          """
            chunk_size = 10000
            for chunk in chunked_data(bulk_data, chunk_size):
                cursor.executemany(insert_sql, chunk)

            cursor.execute("BEGIN")
            # Rename tables
            cursor.execute("ALTER TABLE article_to_cluster_mapping RENAME TO article_to_cluster_mapping_old")
            cursor.execute("COMMIT")
            # cursor.execute("CREATE TABLE article_to_cluster_mapping AS TABLE temp_article_to_cluster_mapping")
            cursor.execute("ALTER TABLE temp_article_to_cluster_mapping RENAME TO article_to_cluster_mapping")
            cursor.execute("DROP TABLE article_to_cluster_mapping_old CASCADE")

    # @staticmethod
    # def save_article_story_cluster_mapping(article_story_cluster_mapping: dict, clustering_run_id: str):
    #     def chunked_data(data, size):
    #         """Yield successive chunk_size-sized chunks from data."""
    #         for i in range(0, len(data), size):
    #             yield data[i:i + size]
    #
    #     with PostgresDatabaseOperation() as cursor:
    #         # Create a temporary table
    #         cursor.execute("CREATE TEMP TABLE temp_article_to_cluster_mapping AS SELECT * FROM article_to_cluster_mapping WHERE 1=0")
    #
    #         # Prepare data for bulk insert
    #         bulk_data = []
    #         for article_id, article_dict in article_story_cluster_mapping.items():
    #             bulk_data.append((
    #                 article_id,
    #                 int(article_dict['storyline_id']),
    #                 int(article_dict['cluster_id']),
    #                 clustering_run_id,
    #                 float(article_dict['storyline_prob']),
    #                 int(article_dict['story_cluster_id']),
    #                 int(article_dict['max_agg_cluster_id']),
    #                 float(article_dict['agg_cluster_prob'])
    #             ))
    #
    #         # Bulk insert in chunks
    #         insert_sql = f"""INSERT INTO temp_article_to_cluster_mapping
    #                          (article_id, storyline_id, cluster_id, clustering_run_id, storyline_prob, story_cluster_id, max_agg_cluster_id, agg_cluster_prob)
    #                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    #                       """
    #         chunk_size = 10000
    #         for chunk in chunked_data(bulk_data, chunk_size):
    #             cursor.executemany(insert_sql, chunk)
    #
    #         # Rename tables
    #         cursor.execute("ALTER TABLE article_to_cluster_mapping RENAME TO article_to_cluster_mapping_old")
    #         cursor.execute("ALTER TABLE temp_article_to_cluster_mapping RENAME TO article_to_cluster_mapping")
    #         cursor.execute("DROP TABLE article_to_cluster_mapping_old CASCADE")

    # with PostgresDatabaseOperation() as cursor:
    #     truncate_sql = f"""TRUNCATE TABLE article_to_cluster_mapping RESTART IDENTITY
    #                     """
    #     cursor.execute(truncate_sql)
    #
    #     insert_sql = f"""INSERT INTO article_to_cluster_mapping
    #                      (article_id, storyline_id, cluster_id, clustering_run_id, storyline_prob, story_cluster_id, max_agg_cluster_id, agg_cluster_prob)
    #                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    #                   """
    #     for article_id in article_storyline_cluster_mapping.keys():
    #         article_dict = article_storyline_cluster_mapping[article_id]
    #         storyline_id = int(article_dict['storyline_id'])
    #         cluster_id = int(article_dict['cluster_id'])
    #         storyline_prob = float(article_dict['storyline_prob'])
    #         story_cluster_id = int(article_dict['story_cluster_id'])
    #         max_agg_cluster_id = int(article_dict['max_agg_cluster_id'])
    #         agg_cluster_prob = float(article_dict['agg_cluster_prob'])
    #         cursor.execute(insert_sql, (article_id, storyline_id, cluster_id, clustering_run_id, storyline_prob, story_cluster_id, max_agg_cluster_id, agg_cluster_prob))

    @staticmethod
    def insert_storyline_to_cluster_mapping(story_to_cluster_mapping: dict, clustering_run_id: str):

        with PostgresDatabaseOperation() as cursor:
            # first truncate the data in live table
            truncate_sql = f"""
                                TRUNCATE TABLE storyline_to_cluster_mapping RESTART IDENTITY
                        """
            cursor.execute(truncate_sql)

            insert_sql = f"""
                            INSERT INTO storyline_to_cluster_mapping (storyline_id, cluster_id, created_at, clustering_run_id)
                            VALUES (%s, %s, %s, %s)
                        """
            history_sql = f"""
                            INSERT INTO storyline_to_cluster_mapping_history (storyline_id, cluster_id, created_at, clustering_run_id)
                            VALUES (%s, %s, %s, %s)
                        """
            current_time = datetime.now()
            for storyline in story_to_cluster_mapping.keys():
                cursor.execute(insert_sql, (storyline, story_to_cluster_mapping[storyline], current_time, clustering_run_id))
                cursor.execute(history_sql, (storyline, story_to_cluster_mapping[storyline], current_time, clustering_run_id))
            # self.connection.commit()
            # cursor.close()

    # TODO: - add support for taking custom run_id
    @staticmethod
    def get_story_to_cluster_mapping() -> (str, dict):
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
        clustering_run_id = df['clustering_run_id'].unique()[0]
        story_to_cluster_mapping = {}
        for mapping in result:
            story_to_cluster_mapping[mapping[0]] = mapping[1]

        return clustering_run_id, story_to_cluster_mapping

    @staticmethod
    def save_cluster_details_for_article_id_to_db(article_id, article_dict: dict, clustering_run_id: str):

        with PostgresDatabaseOperation() as cursor:
            # first truncate the data in live table
            insert_sql = f"""
                            INSERT INTO article_to_cluster_mapping 
                             (article_id, storyline_id, cluster_id, clustering_run_id, storyline_prob, story_cluster_id, max_agg_cluster_id, agg_cluster_prob)
                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                             ON CONFLICT (article_id)
                             DO UPDATE SET
                                storyline_id = EXCLUDED.storyline_id,
                                cluster_id = EXCLUDED.cluster_id,
                                clustering_run_id = EXCLUDED.clustering_run_id,
                                storyline_prob = EXCLUDED.storyline_prob,
                                story_cluster_id = EXCLUDED.story_cluster_id,
                                max_agg_cluster_id = EXCLUDED.max_agg_cluster_id,
                                agg_cluster_prob = EXCLUDED.agg_cluster_prob
                        """
            cursor.execute(insert_sql, (article_id,
                                        int(article_dict['storyline_id']),
                                        int(article_dict['cluster_id']),
                                        clustering_run_id,
                                        article_dict.get('storyline_prob', None),
                                        article_dict.get('story_cluster_id', None),
                                        article_dict.get('max_agg_cluster_id', None),
                                        article_dict.get('agg_cluster_prob', None)
                                        ))
        return

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
    def get_all_run_ids() -> [str]:
        with PostgresDatabaseOperation() as cursor:
            run_id_sql = "SELECT DISTINCT clustering_run_id FROM clustering_runs"
            cursor.execute(run_id_sql)

            result = cursor.fetchall()

        all_run_ids = []
        for value in result:
            all_run_ids.append(value[0])
        return all_run_ids

    @staticmethod
    def get_latest_run_id() -> str:
        with PostgresDatabaseOperation() as cursor:
            run_id_sql = "SELECT DISTINCT clustering_run_id FROM storyline_to_cluster_mapping"
            cursor.execute(run_id_sql)

            result = cursor.fetchall()

        assert len(result) == 1, f"{len(result)} clustering_run_ids found in storyline_to_cluster_mapping - unable to infer unique value"
        return result[0][0]

    @staticmethod
    def get_config_for_run_id(run_id: str) -> dict:
        with PostgresDatabaseOperation() as cursor:
            prev_run_ids = ClusteringSQL.get_all_run_ids()
            assert run_id in prev_run_ids, f"{run_id} not part of previous run ids in clustering_runs table"
            run_config_sql = f"SELECT config FROM clustering_runs WHERE clustering_run_id = %s"
            cursor.execute(run_config_sql, (run_id,))

            result = cursor.fetchall()
        return result[0][0]

    @staticmethod
    def get_storyline_cluster_ids_for_article_id_list(article_ids):
        with PostgresDatabaseOperation() as cursor:
            sql = """SELECT article_id, storyline_id, cluster_id FROM article_to_cluster_mapping WHERE article_id in %s"""
            cursor.execute(sql, (tuple(article_ids),))
            results = cursor.fetchall()
        map_df = pd.DataFrame(results, columns=['article_id', 'storyline_id', 'cluster_id'])
        return {row['article_id']: {'storyline_id': row['storyline_id'], 'cluster_id': row['cluster_id']} for index, row in map_df.iterrows()}

    @staticmethod
    def get_all_story_embeddings() -> dict:
        with PostgresDatabaseOperation() as cursor:
            get_sql = "SELECT story_id, story_embedding, clustering_run_id FROM story_embeddings"
            cursor.execute(get_sql)
            result = cursor.fetchall()
        # converting embeddings into float
        clustering_run_id_set = set([x[2] for x in result])
        assert len(clustering_run_id_set) == 1, f"more than 1 clustering run id found in the story_embeddings"
        result = {x[0]: [float(x[1][k]) for k in range(len(x[1]))] for x in result}
        return result

    @staticmethod
    def insert_story_embeddings(story_embeddings: dict, clustering_run_id):
        with PostgresDatabaseOperation() as cursor:
            truncate_sql = f"""
                            TRUNCATE TABLE story_embeddings RESTART IDENTITY
                            """
            cursor.execute(truncate_sql)

            insert_sql = f"""INSERT INTO story_embeddings (story_id, story_embedding, clustering_run_id)
                            VALUES (%s, %s, %s)
                            """
            # TODO: - can't ideally assume that -1 exists. should come from clustering run - refactor
            if -1 in story_embeddings:
                max_story_idx = len(story_embeddings) - 1
            else:
                max_story_idx = len(story_embeddings)
            # we don't want to save -1 embedding to db - as it doesn't map to any cluster
            for i in range(len(story_embeddings) - 1):
                story_embedding = list(story_embeddings[i])
                cursor.execute(insert_sql, (i, story_embedding, clustering_run_id))

    @staticmethod
    def get_article_ids_with_clusters() -> List[str]:
        with PostgresDatabaseOperation() as cursor:
            get_sql = "SELECT DISTINCT article_id FROM article_to_cluster_mapping WHERE storyline_id NOT IN ('1000', '1001')"
            cursor.execute(get_sql)
            result = cursor.fetchall()
            if len(result) > 0:
                return [row[0] for row in result]
            else:
                return []
