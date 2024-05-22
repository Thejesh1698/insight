import time
from copy import deepcopy
from datetime import datetime
import numpy as np
import pandas as pd
from sql.ArticleSelectionSQL import ArticleSelectionSQL
from src._utils import get_user_cluster_implicit_priors, get_popularity_priors_for_candidates
from sql.ClusteringSQL import ClusteringSQL
from constants import ContentType, SourceType
'''
1. Compute timeliness - temperature
2. Compute popularity - temperature
3. Compute relevance - temperature
'''


# TODO: - validate inputs
# TODO: - error handling?
class ArticleSelectionService:

    def __init__(self):
        # TODO: - meaning that once re-clustering happens, the service should re-start
        self.cluster_names = ClusteringSQL.get_cluster_names()

    # TODO: - mapping of cluster id to article id is missing

    @staticmethod
    def timeliness_score(hours_since_publication, page_number=1, content_type=ContentType.article.value):
        # The function decays a lot in the first few hours and days and then decays slowly. at 6 hours its approximately 1, at 24 hours - 0.93, 3 days at 0.77 and a week at 0.55
        # page number reduces the impact of timeliness weight and also reduces the difference between newer and older articles and page number increases
        hours_since_publication = np.maximum(1, np.array(hours_since_publication))
        page_number = np.maximum(1, np.array(page_number))

        # Vectorized computation
        log_hours = np.log2(hours_since_publication)
        if content_type == ContentType.article.value:
            exponent = (log_hours - 5) / page_number
        else:  # less aggressive decay in case of podcasts, episodes and videos
            exponent = (log_hours - 10) / page_number
        return 0.25 + (0.75 / (1 + np.exp(exponent)))

    @staticmethod
    def get_all_clusters_with_default_preferences():
        clusters = ArticleSelectionSQL.get_all_cluster_ids()
        clusters['explicit_a'] = 1.0
        clusters['explicit_b'] = 6.0
        return clusters

    @staticmethod
    def compute_cluster_preferences(user_id, topic_ids):
        # TODO: - add checks to ensure that
        if not topic_ids:
            explicit_preferences = ArticleSelectionService.get_all_clusters_with_default_preferences()
        else:
            explicit_preferences = ArticleSelectionSQL.get_cluster_pref_for_topics(topic_ids=topic_ids)
        if explicit_preferences.empty:
            explicit_preferences = ArticleSelectionService.get_all_clusters_with_default_preferences()

        explicit_preferences['explicit_a'] = explicit_preferences['explicit_a'].clip(upper=15.0)
        implicit_preferences = get_user_cluster_implicit_priors(user_id=user_id)
        cluster_preferences = pd.merge(explicit_preferences, implicit_preferences, how='left', on='cluster_id')
        cluster_preferences['explicit_a'] = cluster_preferences['explicit_a'].astype('double')
        cluster_preferences['explicit_b'] = cluster_preferences['explicit_b'].astype('double')
        cluster_preferences['explicit_b'] = 15.0
        cluster_preferences = cluster_preferences.fillna({'implicit_a': 0.0, 'implicit_b': 0.0})
        cluster_preferences = cluster_preferences.fillna({'explicit_a': 0.0, 'explicit_b': 0.0})
        cluster_preferences['implicit_a'] = cluster_preferences['implicit_a'].astype('double')
        cluster_preferences['implicit_b'] = cluster_preferences['implicit_b'].astype('double')
        cluster_preferences['cluster_a'] = cluster_preferences['explicit_a'] + cluster_preferences['implicit_a']
        cluster_preferences['cluster_b'] = cluster_preferences['explicit_b'] + cluster_preferences['implicit_b']
        return cluster_preferences

    @staticmethod
    def get_topic_closest_articles(topic_ids):
        if len(topic_ids) > 5:
            topic_ids = np.random.choice(topic_ids, 5)
            topic_ids = [int(x) for x in topic_ids]

        best_articles_df_list = []
        for topic_id in topic_ids:
            cur_topic_articles_df = ArticleSelectionSQL.get_n_closest_articles_for_topic_embedding(topic_id=topic_id, n=500)
            cur_topic_articles_df['topic_id'] = topic_id
            best_articles_df_list.append(cur_topic_articles_df)
        combined_df = pd.concat(best_articles_df_list)
        combined_df = combined_df.groupby('article_id')['cosine_similarity'].max().reset_index()
        combined_df = combined_df.rename(columns={'cosine_similarity': 'relevance_score'})
        return combined_df

    @staticmethod
    def is_eligible_for_embeddings_reco(user_id):
        minute_even = datetime.now().minute % 2 == 0
        # minute_even = True
        # return user_id in [99, 101] and minute_even
        return False

    @staticmethod
    def get_feed(user_id, cur_feed_article_ids, feed_article_count, session_page, topic_ids, seconds_since_last_api_call, content_type):
        start_time = time.time()

        if content_type == SourceType.podcast.value:
            content_id_key = 'source_id'
        else:
            content_id_key = 'article_id'

        candidates_prior_df = get_popularity_priors_for_candidates(content_type=content_type)
        # if user_id in [99, 101]:
        #     user_candidate_articles = candidates
        # else:

        candidates = list(candidates_prior_df[content_id_key].unique())

        user_candidates = ArticleSelectionService._exclude_user_engaged_candidates(user_id=user_id,
                                                                                   candidates=candidates,
                                                                                   cur_feed_content_ids=cur_feed_article_ids,
                                                                                   content_type=content_type)
        if len(user_candidates) < feed_article_count:  # If user exhausted all candidates, then resurface viewed articles
            user_candidates = candidates

        user_candidates_df = candidates_prior_df[candidates_prior_df[content_id_key].isin(user_candidates)]
        cluster_preferences = ArticleSelectionService.compute_cluster_preferences(user_id=user_id, topic_ids=topic_ids)
        user_candidates_df = pd.merge(user_candidates_df, cluster_preferences, how='left', on='cluster_id')
        user_candidates_df = user_candidates_df.fillna({'cluster_a': 1.0, 'cluster_b': 5.0})  # in an unlikely case where candidate's cluster doesn't have a match
        user_candidates_df['timeliness_score'] = ArticleSelectionService.timeliness_score(user_candidates_df['hours_since_publication'], page_number=session_page,
                                                                                          content_type=content_type)
        use_cosine_for_relevance = False
        reco_model = 'thompson_sampling_llm_v3'

        if ArticleSelectionService.is_eligible_for_embeddings_reco(user_id=user_id):
            # TODO: - support source_id for this
            closest_articles = ArticleSelectionService.get_topic_closest_articles(topic_ids=topic_ids)
            filtered_user_candidates_df = pd.merge(user_candidates_df, closest_articles, how='inner', on='article_id')
            filtered_user_candidates_df = filtered_user_candidates_df[filtered_user_candidates_df['relevance_score'] >= 0.63]
            print(len(filtered_user_candidates_df))
            if len(filtered_user_candidates_df) >= feed_article_count:
                use_cosine_for_relevance = True
                reco_model = 'thompson_sampling_llm_v2_topic_embeddings'
                user_candidates_df = filtered_user_candidates_df

        if not use_cosine_for_relevance:
            user_candidates_df['relevance_score'] = np.random.beta(user_candidates_df['cluster_a'], user_candidates_df['cluster_b'])

        if seconds_since_last_api_call is None:  # for first ever feed. based on initial weights, 0.6 is for ~ < 6 days old article
            user_candidates_sub_df = user_candidates_df[(user_candidates_df['relevance_score'] >= 0.5) & (user_candidates_df['timeliness_score'] >= 0.6)]
            if len(user_candidates_sub_df) > feed_article_count:
                user_candidates_df = user_candidates_sub_df
        user_candidates_df['popularity_score'] = np.random.beta(user_candidates_df['article_a'], user_candidates_df['article_b'])
        # user_candidates_df['scaled_popularity_score'] = user_candidates_df['popularity_score']/max(user_candidates_df['popularity_score'])
        user_candidates_df['scaled_relevance_score'] = user_candidates_df['relevance_score'] / max(user_candidates_df['relevance_score'])
        # normalized total score with weights of 2 for timeliness, 1 for relevance and 1 for popularity
        timeliness_weight = 1
        relevance_weight = 1
        popularity_weight = 0.25
        total_weight = timeliness_weight + relevance_weight + popularity_weight
        user_candidates_df['timeliness_weight'] = timeliness_weight
        user_candidates_df['relevance_weight'] = relevance_weight
        user_candidates_df['popularity_weight'] = popularity_weight
        user_candidates_df['total_score'] = (user_candidates_df['timeliness_weight'] * user_candidates_df['timeliness_score'] + user_candidates_df['relevance_weight'] * user_candidates_df['scaled_relevance_score'] + user_candidates_df['popularity_weight'] * user_candidates_df['popularity_score'])/total_weight
        response_df = user_candidates_df.nlargest(feed_article_count, 'total_score')
        feed_response = ArticleSelectionService.format_response(response_df, content_id_key=content_id_key, model=reco_model)
        print(f'completed feed computation in {(time.time() - start_time) * 1000}  ms')
        return feed_response

    # TODO NEW: - enable showing interacted articles again
    # TODO NEW: - heirarchical selection of articles
    # TODO NEW: - once user searches for a keyword - assign those to cluster probabilities
    # TODO: - get overall a, b for all the candidate articles - using a query on user-article interaction table
    # TODO: - use user-article interaction table to filter out previously engaged articles

    @staticmethod
    def _exclude_user_engaged_candidates(user_id, candidates, cur_feed_content_ids, content_type) -> list:
        if content_type in [ContentType.article.value, ContentType.podcast_episode.value]:
            all_user_engaged_articles = ArticleSelectionSQL.get_user_past_feed_articles(user_id=user_id)
            # TODO: - add the logic of ignored multiple times later
            candidates = list(set(candidates) - set(all_user_engaged_articles))
        candidates = list(set(candidates) - set(cur_feed_content_ids))
        return candidates

    @staticmethod
    def format_response(feed_df, content_id_key, model='thompson_sampling_llm_v2'):
        feed_list = feed_df.to_dict('records')
        feed_content_list = [{'content_id': x[content_id_key]} for x in feed_list]
        additional_info = {}
        for article_data in feed_list:
            cur_info = deepcopy(article_data)
            content_id = cur_info.pop(content_id_key)
            additional_info[content_id] = cur_info
        response = {'feedContents': feed_content_list, 'model': model, 'additionalInfo': additional_info}
        return response

    # def _format_response(self, feed_articles_df, cluster_preferences):
    #     feed_articles_list = feed_articles_df[['article_id', 'cluster_id', 'a', 'b', 'sample_probability']].to_dict('records')
    #     additional_info = self._get_metadata_for_articles_clusters(feed_articles_list=feed_articles_list,
    #                                                                cluster_preferences=cluster_preferences,
    #                                                                cluster_names=self.cluster_names)
    #     feed_articles_list = [{'article_id': x['article_id']} for x in feed_articles_list]
    #     feed_response = {'feedArticles': feed_articles_list, 'model': 'thompson_sampling_v1', 'additionalInfo': additional_info}
    #     return feed_response

    @staticmethod
    def _get_metadata_for_articles_clusters(feed_articles_list, cluster_preferences, cluster_names):
        article_id_list = [x['article_id'] for x in feed_articles_list]
        article_storyline_clusters = ClusteringSQL.get_storyline_cluster_ids_for_article_id_list(article_id_list)

        additional_info = {}
        for article_data in feed_articles_list:
            article_id = article_data['article_id']
            storyline_id = article_storyline_clusters[article_id]['storyline_id']
            cluster_id = article_storyline_clusters[article_id]['cluster_id']
            cur_additional_info = {key: article_data[key] for key in ['cluster_id', 'sample_probability']}

            cur_additional_info['article_a'] = round(article_data['a'], 3)
            cur_additional_info['article_b'] = round(article_data['b'], 3)
            cur_additional_info['storyline'] = cluster_names.get(storyline_id, 'outlier')
            cur_additional_info['cluster'] = cluster_names[cluster_id]
            cur_additional_info['implicit_a'] = round(cluster_preferences[cluster_id]['implicit_a'], 3)
            cur_additional_info['explicit_a'] = round(cluster_preferences[cluster_id]['explicit_a'], 3)
            cur_additional_info['implicit_b'] = round(cluster_preferences[cluster_id]['implicit_b'], 3)
            cur_additional_info['explicit_b'] = round(cluster_preferences[cluster_id]['explicit_b'], 3)
            cur_additional_info['sample_probability'] = round(cur_additional_info['sample_probability'], 3)
            additional_info[article_id] = cur_additional_info

        return additional_info
