import numpy as np
from copy import deepcopy
from random import choice
from typing import Dict, Union, List
import logging
from sql.ClusteringSQL import ClusteringSQL
from sql.ArticleSelectionSQL import ArticleSelectionSQL
from src._utils import apply_user_pref_decay_by_feed_date

ClusterPreferenceType = Dict[int, Dict[str, float]]


# TODO: - add logic for max documents per cluster if there are more clusters
# TODO: - explicit cluster preferences is sorted
# TODO: -
# TODO: - article - user interaction data will be in ML data
class ClusterPreferenceService:

    def __init__(self):
        self.probability_powers = self.__compute_probability_powers()
        # TODO: - refactor to fetch on runtime
        self.storyline_to_cluster_mapping = ClusteringSQL.get_story_to_cluster_mapping()
        self.clusters = list(set(self.storyline_to_cluster_mapping.values()))
        self.default_b_value = np.round(np.log(len(self.clusters)))
        self.max_a_prior_value = self.default_b_value * 2

    def get_overall_user_preferences(self, user_id, topic_id_list):
        explicit_preferences = self.get_cluster_preferences_for_topic_list(topic_id_list=topic_id_list)
        implicit_preferences = self.get_implicit_user_preferences(user_id=user_id)
        overall_pref = self.merge_explicit_implicit_cluster_priors(explicit_priors=explicit_preferences, implicit_priors=implicit_preferences)
        return overall_pref

    @staticmethod
    def merge_explicit_implicit_cluster_priors(explicit_priors, implicit_priors):
        # Initialize the merged dictionary with default values.
        merged_dict = {cluster_id: {'a': 0, 'b': 0, 'explicit_a': 0, 'explicit_b': 0, 'implicit_a': 0, 'implicit_b': 0}
                       for cluster_id in set(explicit_priors) | set(implicit_priors)}

        # Helper function to update the dictionary with new priors.
        def update_dict(target_dict, prior_dict, prefix):
            for cluster_id, value in prior_dict.items():
                target_dict[cluster_id][f'{prefix}_a'] = value['a']
                target_dict[cluster_id][f'{prefix}_b'] = value['b']
                target_dict[cluster_id]['a'] += value['a']
                target_dict[cluster_id]['b'] += value['b']

        # Update the merged dictionary with explicit and implicit priors.
        update_dict(merged_dict, explicit_priors, 'explicit')
        update_dict(merged_dict, implicit_priors, 'implicit')

        # Ensure 'a' and 'b' are at least 1.
        for priors in merged_dict.values():
            priors['a'] = max(1, priors['a'])
            priors['b'] = max(1, priors['b'])

        return merged_dict

    @staticmethod
    def get_implicit_user_preferences(user_id: int):
        user_cluster_df = ArticleSelectionSQL.get_user_day_wise_cluster_a_b(user_id=user_id)
        # TODO: - add validations on df
        user_cluster_df = apply_user_pref_decay_by_feed_date(df=user_cluster_df)
        user_cluster_df['scaled_a'] = user_cluster_df['a'] * user_cluster_df['decay']
        user_cluster_df['scaled_b'] = user_cluster_df['b'] * user_cluster_df['decay']
        implicit_pref = {}
        for index, row in user_cluster_df.iterrows():
            implicit_pref[row['cluster_id']] = {'a': row['scaled_a'], 'b': row['scaled_b']}
        return implicit_pref

    @staticmethod
    def __sample_cluster_probabilities(cluster_prefs: Dict, feed_article_count: int) -> Dict:
        num_clusters = len(cluster_prefs)
        num_consideration_clusters = min(feed_article_count // 2, num_clusters)
        cluster_wise_prob = {cluster: np.round(np.random.beta(cluster_prefs[cluster]['a'], cluster_prefs[cluster]['b']), 3) for cluster in cluster_prefs.keys()}
        top_clusters = sorted(cluster_wise_prob, key=cluster_wise_prob.get, reverse=True)[:num_consideration_clusters]
        cluster_wise_prob = {cluster: cluster_wise_prob[cluster] for cluster in top_clusters}
        return cluster_wise_prob

    @staticmethod
    def __compute_probability_powers():
        probability_powers = {}
        for i in range(1001):  # 0.00, 0.01, ..., 1.00
            prob = i / 1000.0
            probability_powers[prob] = {}
            for power in [x * 0.5 for x in range(1, 41)]:
                probability_powers[prob][power] = np.round(prob ** power, 3)
        return probability_powers

    def get_cluster_preferences_for_topic_list(self, topic_id_list: List[int]):
        # get topic level dict of cluster preferences
        all_preferences = ArticleSelectionSQL.get_all_topic_preferences_from_db()
        valid_topics = list(all_preferences['topic_id'].unique())
        valid_topic_id_list = list(set(valid_topics).intersection(set(topic_id_list)))
        topic_cluster_prior_list = {}
        for topic_id in valid_topic_id_list:
            topic_cluster_prior = {}
            for row in all_preferences[all_preferences['topic_id'] == topic_id][['cluster_id', 'a', 'b']].itertuples():
                topic_cluster_prior[row.cluster_id] = {'a': float(row.a), 'b': float(row.b)}
            topic_cluster_prior_list[topic_id] = topic_cluster_prior

        # merge
        if len(topic_cluster_prior_list) > 0:
            merged_cluster_preferences = self.__merge_explicit_cluster_priors(cluster_prior_list=list(topic_cluster_prior_list.values()))
            return merged_cluster_preferences
        else:  # if the topic ids are not valid or if empty topic id list
            return {cluster: {'a': 1.0, 'b': self.default_b_value} for cluster in self.clusters}

    def __merge_explicit_cluster_priors(self, cluster_prior_list):
        merged_dict = {}

        for d in cluster_prior_list:
            for key, value in d.items():
                if key not in merged_dict:
                    merged_dict[key] = value
                else:
                    # Merge 'a' values using the given logic: 1 + (a1-1) + (a2-1)
                    merged_dict[key]['a'] = min(self.max_a_prior_value, 1 + (merged_dict[key]['a'] - 1) + (value['a'] - 1))

                    # Merge 'b' values by taking the average
                    merged_dict[key]['b'] = (merged_dict[key]['b'] + value['b']) / 2

        return merged_dict


# Initialize logging
logging.basicConfig(level=logging.INFO)