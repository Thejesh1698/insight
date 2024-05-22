from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
from typing import List, Dict
import pandas as pd
from constants import INTERACTIONS_CUTOFF_DATE, INTERACTIONS_EXCLUSION_USERS, SUMMARY_WEIGHTAGE, NON_FIN_CLUSTER_ID


class ArticleSelectionSQL:

    @staticmethod
    # TODO: - exclude data before 26 feb and exclude dev
    def get_day_wise_candidate_article_ab(content_type):
        with PostgresDatabaseOperation() as cursor:
            candidates_interaction = f"""
                WITH truncated_uai AS (SELECT * FROM user_article_interactions WHERE created_at > '{INTERACTIONS_CUTOFF_DATE}' AND user_id != {INTERACTIONS_EXCLUSION_USERS})
                (SELECT ca.article_id, 
                source_id,
                cluster_id,
                CAST(ca.published_at AS TIMESTAMP) as published_time, 
                CAST(uai.created_at AS DATE) as activity_date,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN CAST(is_article_opened AS INT) ELSE 0 END) as feed_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN COALESCE(CAST(is_summary_read AS INT), 0) ELSE 0 END) as feed_summary_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN greatest(CAST(is_article_opened AS int), {SUMMARY_WEIGHTAGE} * COALESCE(CAST(is_summary_read AS int), 0)) ELSE 0 END) as total_feed_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' AND CAST(is_article_opened AS INT) = 0 AND COALESCE(CAST(is_summary_read AS INT), 0) = 0 THEN 1 ELSE 0 END) as feed_b,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN CAST(is_article_opened AS INT) ELSE 0 END) as search_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN COALESCE(CAST(is_summary_read AS INT), 0) ELSE 0 END) as search_summary_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN greatest(CAST(is_article_opened AS int), {SUMMARY_WEIGHTAGE} * COALESCE(CAST(is_summary_read AS int), 0)) ELSE 0 END) as total_search_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' AND CAST(is_article_opened AS INT) = 0 AND COALESCE(CAST(is_summary_read AS INT), 0) = 0 THEN 1 ELSE 0 END) as search_b,
                MIN(ca.prior_a) as prior_a,
                MIN(ca.prior_b) as prior_b
                FROM candidate_articles ca 
                LEFT JOIN article_to_cluster_mapping acm
                ON ca.article_id = acm.article_id
                LEFT JOIN truncated_uai uai
                    ON uai.article_id = ca.article_id
                WHERE content_type = '{content_type}'
                AND cluster_id != {NON_FIN_CLUSTER_ID}
                GROUP BY ca.article_id, source_id, cluster_id, published_time, activity_date
                ORDER BY total_feed_a desc)
                """
            cursor.execute(candidates_interaction)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['article_id', 'source_id', 'cluster_id', 'published_time', 'activity_date', 'feed_a', 'feed_summary_a', 'total_feed_a', 'feed_b', 'search_a', 'search_summary_a', 'total_search_a', 'search_b', 'prior_a', 'prior_b'])
        return df

    @staticmethod
    def get_cluster_pref_for_topics(topic_ids: List[int]):
        with PostgresDatabaseOperation() as cursor:
            merged_preferences = f"""
            SELECT parent_name, cluster_id, 1 + sum(a-1) explicit_a, avg(b) explicit_b 
            FROM topic_cluster_preference_mapping tcm LEFT JOIN cluster_hierarchy ch ON tcm.cluster_id = ch.parent_id
            WHERE topic_id in %s
            GROUP BY parent_name, cluster_id
            """
            cursor.execute(merged_preferences, (tuple(topic_ids),))
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['cluster_name', 'cluster_id', 'explicit_a', 'explicit_b'])
        return df

    @staticmethod
    def get_all_cluster_ids():
        with PostgresDatabaseOperation() as cursor:
            clusters = f"""
            SELECT DISTINCT parent_name, cluster_id
            FROM topic_cluster_preference_mapping tcm LEFT JOIN cluster_hierarchy ch ON tcm.cluster_id = ch.parent_id 
            """
            cursor.execute(clusters)
            results = cursor.fetchall()
        df = pd.DataFrame(results, columns=['cluster_name', 'cluster_id'])
        return df

    @staticmethod
    def get_n_closest_articles_for_topic_embedding(topic_id: int, n=50, approach_name='gpt4-keywords-v2', content_type='ARTICLE'):
        # SET LOCAL ivfflat.probes = 10;
        with PostgresDatabaseOperation() as cursor:
            sql = f"""
                SELECT ca.article_id, 
                       1- (embedding <=> description_embedding) AS cosine_sim
                    FROM candidate_articles ca
                    LEFT JOIN embeddings e
                    ON ca.article_id = e.article_id
                    cross JOIN topic_internal_representations tir
                    WHERE topic_id = %s
                    AND approach_name = %s
                    AND content_type = {content_type}
                    ORDER BY embedding <=> description_embedding
                    LIMIT %s;
                """
            cursor.execute(sql, (topic_id, approach_name, n))
            results = cursor.fetchall()
        return pd.DataFrame(results, columns=['article_id', 'cosine_similarity'])

    @staticmethod
    # TODO: - old
    def get_day_wise_article_a_b() -> pd.DataFrame:
        # TODO: - to evaluate if we need to take count distinct for feed id in case articles can duplicate
        # TODO: - do this only for candidate articles
        with PostgresDatabaseOperation() as cursor:
            interaction_sql = f"""SELECT article_id, CAST(created_at AS DATE) as feed_date, SUM(CAST(is_article_opened AS INT)) as a, COUNT(activity_id) as b
                                FROM user_article_interactions 
                                WHERE created_at > '{INTERACTIONS_CUTOFF_DATE}' AND user_id != {INTERACTIONS_EXCLUSION_USERS}
                                GROUP BY article_id, feed_date 
                                """
            cursor.execute(interaction_sql)
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['article_id', 'feed_date', 'a', 'b'])
            return df

    @staticmethod
    def get_user_past_feed_articles(user_id: int) -> List[str]:
        with PostgresDatabaseOperation() as cursor:
            opened_sql = f"""SELECT DISTINCT article_id FROM user_article_interactions WHERE user_id = %s AND activity_type = 'USER_FEED'"""
            cursor.execute(opened_sql, (user_id,))
            results = cursor.fetchall()
            if len(results) > 0:
                return [row[0] for row in results]
            else:
                return []

    @staticmethod
    def get_user_day_wise_cluster_activity_a_b(user_id: int) -> pd.DataFrame:
        with PostgresDatabaseOperation() as cursor:
            interaction_sql = f"""
                SELECT 
                cluster_id,
                CAST(uai.created_at AS DATE) as activity_date,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN CAST(is_article_opened AS INT) ELSE 0 END) as feed_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN COALESCE(CAST(is_summary_read AS INT), 0) ELSE 0 END) as feed_summary_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' THEN greatest(CAST(is_article_opened AS int), {SUMMARY_WEIGHTAGE} * COALESCE(CAST(is_summary_read AS int), 0)) ELSE 0 END) as total_feed_a,
                SUM(CASE WHEN activity_type = 'USER_FEED' AND is_article_opened = false AND COALESCE(CAST(is_summary_read AS INT), 0) = 0  THEN 1 ELSE 0 END) as feed_b,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN CAST(is_article_opened AS INT) ELSE 0 END) as search_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN COALESCE(CAST(is_summary_read AS INT), 0) ELSE 0 END) as search_summary_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' THEN greatest(CAST(is_article_opened AS int), {SUMMARY_WEIGHTAGE} * COALESCE(CAST(is_summary_read AS int), 0)) ELSE 0 END) as total_search_a,
                SUM(CASE WHEN activity_type = 'ARTICLES_SEARCH' AND is_article_opened = false AND COALESCE(CAST(is_summary_read AS INT), 0) = 0 THEN 1 ELSE 0 END) as search_b 
                FROM user_article_interactions uai 
                INNER JOIN article_to_cluster_mapping acm
                ON uai.article_id = acm.article_id
                WHERE user_id = %s  AND uai.created_at > '{INTERACTIONS_CUTOFF_DATE}'
                GROUP BY cluster_id, activity_date
                                """
            cursor.execute(interaction_sql, (user_id,))
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['cluster_id', 'activity_date', 'feed_a', 'feed_summary_a', 'total_feed_a', 'feed_b', 'search_a', 'search_summary_a', 'total_search_a', 'search_b'])
            return df

    @staticmethod
    # TODO: - old
    def get_user_day_wise_cluster_a_b(user_id: int) -> pd.DataFrame:
        with PostgresDatabaseOperation() as cursor:
            interaction_sql = f"""
            SELECT cluster_id, 
            CAST(uai.created_at AS DATE) as feed_date, 
            SUM(CAST(is_article_opened AS INT)) as a, SUM(COALESCE(CAST(is_summary_read AS INT), 0)) as summary_a, COUNT(activity_id) as b 
              FROM user_article_interactions uai LEFT JOIN article_to_cluster_mapping acm
              ON uai.article_id = acm.article_id
              WHERE user_id = %s AND uai.created_at > '2024-02-26'
              GROUP BY cluster_id, feed_date
                            """
            cursor.execute(interaction_sql, (user_id,))
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['cluster_id', 'feed_date', 'a', 'summary_a', 'b'])
            return df

    @staticmethod
    # TODO: - old
    def get_candidate_articles() -> pd.DataFrame:
        with PostgresDatabaseOperation() as cursor:
            sql = """SELECT DISTINCT ca.article_id, cluster_id FROM candidate_articles ca 
            LEFT JOIN article_to_cluster_mapping acm 
            ON ca.article_id = acm.article_id
            """
            cursor.execute(sql, )
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['article_id', 'cluster_id'])
            return df

    @staticmethod
    def get_storyline_cluster_ids_for_article_id_list(article_ids):
        with PostgresDatabaseOperation() as cursor:
            sql = """SELECT article_id, storyline_id, cluster_id FROM article_to_cluster_mapping WHERE article_id in %s"""
            cursor.execute(sql, (tuple(article_ids),))
            results = cursor.fetchall()
        map_df = pd.DataFrame(results, columns=['article_id', 'storyline_id', 'cluster_id'])
        return {row['article_id']: {'storyline_id': row['storyline_id'], 'cluster_id': row['cluster_id']} for index, row in map_df.iterrows()}

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
    def get_all_topic_preferences_from_db() -> pd.DataFrame:
        with PostgresDatabaseOperation() as cursor:
            sql = "SELECT topic_id, topic_name, cluster_id, a, b, clustering_run_id, created_at FROM topic_cluster_preference_mapping"
            cursor.execute(sql)
            results = cursor.fetchall()
            df = pd.DataFrame(results, columns=['topic_id', 'topic_name', 'cluster_id', 'a', 'b', 'clustering_run_id', 'created_at'])

        return df
