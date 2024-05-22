import logging
from collections import defaultdict
from omegaconf import DictConfig
from typing import List, Dict
import numpy as np
from bertopic import BERTopic

from constants import BACKEND_URL
from src.data_models.ClusterPreferenceData import ClusterPreferenceData
from sql.clustering.ClusteringSQL import ClusteringSQL
from sql.onboarding.TopicPreferencesSQL import TopicPreferencesSQL
import requests
import json

OUTLIER_CLUSTER = -1

# TODO: - get topic name using topic id and use topic id instead of topic name


class TopicClusterMapping:

    def __init__(self, clustering_run_id: str, bertopic_model: BERTopic, cfg: DictConfig):
        """
        :param cfg: DictConfig
        """
        self._verify_config(cfg)
        self.cfg = cfg
        self.clustering_run_id = clustering_run_id
        self.story_embeddings = ClusteringSQL.get_all_story_embeddings()
        self.bertopic_model = bertopic_model
        # TODO: - should we refactor to use some global project level objects?
        mapping_clustering_run_id, self.storyline_to_cluster_mapping = ClusteringSQL.get_story_to_cluster_mapping()
        assert mapping_clustering_run_id == clustering_run_id, f"init run_id {clustering_run_id} is different from run id  {mapping_clustering_run_id} with story cluster mapping"
        self.clusters = list(set(self.storyline_to_cluster_mapping.values()))
        self.storyline_to_cluster_mapping[OUTLIER_CLUSTER] = OUTLIER_CLUSTER

        # Assert that all topics in the mapping are valid
        for topic in self.bertopic_model.topic_labels_.keys():
            assert topic in self.storyline_to_cluster_mapping, f"No mapping for topic {topic}"

        # Pre-calculate some values for performance and use in later methods
        num_clusters = len(self.clusters)
        # The default not clicked value is increasingly pessimistic as number of clusters increase.
        # TOdo: - centralize this logic of
        self.default_b_value = np.round(np.log(num_clusters))
        self.position_log_scaling = self._pre_compute_position_log_scaling()

    @staticmethod
    def _verify_config(cfg: DictConfig) -> None:
        required_keys = ['similarity_position_log', 'max_a_prior_value', 'num_similar_topics']
        for key in required_keys:
            assert key in cfg, f"Key {key} not found in configuration"

    def _pre_compute_position_log_scaling(self) -> Dict[int, float]:
        """Pre-compute the log scaling based on index for performance."""
        return {i: self._compute_position_log_scaling_for_idx(i) for i in range(101)}

    def _compute_position_log_scaling_for_idx(self, idx: int) -> float:
        """Compute the log scaling based on the index."""
        return np.log10(idx + 2) / np.log10(self.cfg.similarity_position_log)
    #
    # def compute_cluster_preferences(self, topic_keywords: List[str]) -> dict:
    #     """
    #      Compute and return the cluster preferences based on the given topic keywords.
    #
    #      :param topic_keywords: List of topic keywords.
    #      :return: A dictionary containing cluster preferences.
    #      """
    #     # Initialize priors for each cluster
    #     cluster_priors = ClusterPreferenceData({cluster: {'a': 1.0, 'b': self.default_b_value} for cluster in self.clusters})
    #     for topic in topic_keywords:
    #         cluster_priors = self._update_cluster_priors_for_keyword(topic, cluster_priors)
    #     return cluster_priors.data

    def _update_cluster_priors_for_keyword(self, word: str, cluster_priors: ClusterPreferenceData) -> ClusterPreferenceData:
        """
        Update cluster priors based on a given keyword.

        :param word: The keyword for which to update the cluster priors.
        :param cluster_priors: The existing cluster priors.
        :return: Updated cluster priors.
        """
        cluster_scores = self._compute_top_similar_clusters_for_word(word)
        for cluster, score in cluster_scores.items():
            if cluster == OUTLIER_CLUSTER:       # Skip the outlier cluster
                continue
            new_a_value = min(self.cfg.max_a_prior_value, score + cluster_priors.get_cluster_a_data(cluster_id=cluster))
            cluster_priors.update_cluster_a_data(cluster_id=cluster, new_a=np.round(new_a_value, 3))
        return cluster_priors

    @staticmethod
    def _get_all_topics():
        topic_url = f'{BACKEND_URL}/public/articles/topics'
        r = requests.get(topic_url)
        all_topics = json.loads(r.text)
        # TODO: - add validations
        return all_topics['topics']

    def recompute_preferences_for_all_topics(self):
        # DONE: - test this logic
        logging.info('recomputing preferences for all topics')
        all_topics = TopicClusterMapping._get_all_topics()
        logging.info('all topics fetched')
        # TODO: - migrate to bulk save and truncate in the same query - not separately
        TopicPreferencesSQL.reset_all_topic_preferences_in_db()
        logging.info('all preferences are reset')
        # all_topic_ids = [x['topicId'] for x in topics]
        for topic in all_topics:
            topic_name = f"{topic['category']}: {topic['topicName']}"
            self.compute_and_save_cluster_priors_for_topic_id(topic_id=topic['topicId'], topic_name=topic_name)
            logging.info(f'priors computed and saved for topic {topic_name}')

    def get_cluster_preferences_for_topic_list(self, topic_id_list: List[int]):
        # get topic level dict of cluster preferences
        all_preferences = TopicPreferencesSQL.get_all_topic_preferences_from_db()
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
                    merged_dict[key]['a'] = min(self.cfg.max_a_prior_value, 1 + (merged_dict[key]['a'] - 1) + (value['a'] - 1))

                    # Merge 'b' values by taking the average
                    merged_dict[key]['b'] = (merged_dict[key]['b'] + value['b']) / 2

        return merged_dict

    def compute_and_save_cluster_priors_for_topic_id(self, topic_id: int, topic_name: str):
        # TODO: - replace with some logic of fetching from api
        # topic_name = topics[topic_id]
        # TODO: - add logic to get the appropriate description and save back to db
        cluster_priors = self._compute_cluster_priors_for_keyword(word=topic_name)
        TopicPreferencesSQL.save_topic_preferences_to_db(topic_id=topic_id, topic_name=topic_name, topic_cluster_preferences=cluster_priors,
                                                         clustering_run_id=self.clustering_run_id)

    def _compute_cluster_priors_for_keyword(self, word: str) -> Dict[int, Dict[str, float]]:
        cluster_scores = self._compute_top_similar_clusters_for_word(word)
        cluster_priors = {cluster: {'a': 1.0, 'b': self.default_b_value} for cluster in self.clusters}
        for cluster, score in cluster_scores.items():
            if cluster == OUTLIER_CLUSTER:       # Skip the outlier cluster
                continue
            new_a_value = min(self.cfg.max_a_prior_value, score + cluster_priors.get(cluster, {}).get('a', 1.0))
            cluster_priors[cluster]['a'] = new_a_value
        return cluster_priors

    def _compute_top_similar_clusters_for_word(self, word: str) -> Dict[int, float]:
        """
        Compute cluster scores for a given keyword.

        :param word: The keyword for which to compute cluster scores.
        :return: A dictionary containing the cluster scores.
        """

        # Get similar topics and their similarity scores
        similar_topics, similarity = self.bertopic_model.find_topics(word, top_n=self.cfg.num_similar_topics)
        similarity = np.array(similarity)

        # Compute position scaling for each similarity score
        position_scaling = np.array([self.position_log_scaling.get(idx, self._compute_position_log_scaling_for_idx(idx)) for idx in range(len(similarity))])
        # TODO: - check the similarity distribution with the new model
        modified_similarity = ((similarity - 0.01) / (1 - 0.01)) * np.minimum(1, 1 / position_scaling)
        similar_clusters = np.array([self.storyline_to_cluster_mapping.get(topic, OUTLIER_CLUSTER) for topic in similar_topics])

        result = defaultdict(float)
        for cluster, sim in zip(similar_clusters, modified_similarity):
            result[cluster] += sim

        return dict(result)
