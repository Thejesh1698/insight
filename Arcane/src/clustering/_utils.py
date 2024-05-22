import os
import random
import string
import numpy as np
import pandas as pd
from typing import Dict, List
from sql.clustering.ClusteringSQL import ClusteringSQL

# TOD0: - define as global constants
OUTLIER = -1


def __get_balanced_cluster_for_outlier(story_cluster_map: dict, article_story_probs: np.array) -> (int, float):
    balanced_cluster_indices = [story_cluster_map.get(t, -1) for t in range(len(article_story_probs))]
    # Find the cluster with the maximum total probability
    df = pd.DataFrame({'balanced_cluster': balanced_cluster_indices, 'probability': article_story_probs})
    doc_cluster_prob_df = df.groupby('balanced_cluster').sum()
    best_balanced_cluster = doc_cluster_prob_df['probability'].idxmax()
    best_balanced_cluster_prob = doc_cluster_prob_df['probability'].max()
    return int(best_balanced_cluster), best_balanced_cluster_prob


def assign_article_to_cluster(article_story_id: int, article_story_probs: np.array, story_cluster_map: dict) -> dict:
    # For each outlier, find the most probable cluster
    article_dict = {'storyline_id': int(article_story_id)}    # we are using int to make the dict json serializable
    if article_story_id == OUTLIER:
        article_dict['storyline_prob'] = 1 - np.sum(article_story_probs)
        article_dict['story_cluster_id'] = int(OUTLIER)
    else:
        article_dict['storyline_prob'] = article_story_probs[article_story_id]
        article_dict['story_cluster_id'] = int(story_cluster_map[article_story_id])

    article_dict['max_agg_cluster_id'], article_dict['agg_cluster_prob'] = __get_balanced_cluster_for_outlier(story_cluster_map=story_cluster_map,
                                                                                                              article_story_probs=article_story_probs)
    if article_story_id == OUTLIER:
        article_dict['cluster_id'] = article_dict['max_agg_cluster_id']
    else:
        article_dict['cluster_id'] = article_dict['story_cluster_id']
    return article_dict


def __load_words_from_file() -> list:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    words_file_path = os.path.join(script_dir, 'words.txt')
    if os.path.exists(words_file_path):
        with open(words_file_path, 'r') as file:
            words = []
            for line in file:
                line = line.strip()
                words.append(line)
        return words
    else:
        return []


def generate_unique_run_id() -> str:
    words = __load_words_from_file()
    prev_run_ids = ClusteringSQL.get_all_run_ids()

    def get_run_id():
        if words and len(words) > 100:
            random_id = ''.join(random.sample(words, 3))
        else:
            characters = string.ascii_letters
            random_id = ''.join(random.choice(characters) for i in range(8))
        return random_id

    run_id = get_run_id()
    # to handle clashes
    while run_id in prev_run_ids:
        run_id = get_run_id()

    return run_id
