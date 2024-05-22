import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
from copy import deepcopy
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from datasets import load_dataset
from umap import UMAP
import re
from hdbscan import HDBSCAN
from bertopic.representation import KeyBERTInspired
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
import plotly.io as pio
pio.renderers.default = 'iframe'
import dill

class EmbeddingsClusterTopics:
    def __init__(self, model_name, dataset_path, documents_column_name, embeddings_column_name, clustering_type = 'hdbscan', random_state = None):
        self.model_name = model_name
        self.embeddings_model = SentenceTransformer(self.model_name)
        custom_umap_model = UMAP(n_neighbors=15, n_components=10, random_state=random_state)  # Change 10 to the desired number of dimensions
        if clustering_type == 'hdbscan':
            custom_hdbscan_model = HDBSCAN(metric = 'manhattan')
        elif clustering_type == 'kmeans':
            custom_hdbscan_model = KMeans(n_clusters=25, random_state=random_state)
        vectorizer_model = CountVectorizer(stop_words="english", min_df=2, ngram_range=(1, 2))
        representation_model = KeyBERTInspired()
        self.bertopic_model = BERTopic(# representation_model=representation_model,
                                      calculate_probabilities = True)
        self.dataset = load_dataset('parquet',data_files =dataset_path)['train']
        self.documents = self._load_documents_from_parquet(documents_column_name)
        self.documents = [self._remove_numeric_words(doc) for doc in self.documents]
        self.embeddings = self._load_embeddings_from_parquet(embeddings_column_name)
        self.create_clusters_topics()
        self.generate_topic_names()

    def _remove_numeric_words(self, text):
        # Remove currency-based numbers like $123.1, currency symbols like €, and rupee symbol ₹
        currency_pattern = r'\$\s*\d+(\.\d+)?|\€\s*\d+(\.\d+)?|₹\s*\d+(\.\d+)?'

        # Match numeric words or currency-based numbers
        numeric_pattern = r'\b\d+(\.\d+)?\b'

        # Combine both patterns using negative lookahead to exclude percentages
        combined_pattern = rf'(?!(?:\d+(\.\d+)?%))({currency_pattern}|{numeric_pattern})'

        cleaned_text = re.sub(combined_pattern, '', text)
        return cleaned_text

    def _load_embeddings_from_parquet(self, embeddings_column_name):
        return np.array(self.dataset[embeddings_column_name])

    def _load_documents_from_parquet(self, documents_column_name):
        return self.dataset[documents_column_name]

    def create_clusters_topics(self):
        topics, _ = self.bertopic_model.fit_transform(documents = self.documents, embeddings = self.embeddings)
        self.hierarchical_topics = self.bertopic_model.hierarchical_topics(self.documents)

    def generate_topic_names(self):
        return self.bertopic_model.generate_topic_labels(nr_words=5, separator=", ")
    

class TopicHierarchy:
    def __init__(self, df, topic_to_doc_indices):
        self.df = df
        # self.levels = {}
        self.raw_leaf_points_count = {}
        self.raw_leaf_points_list = {}
        self.topic_to_doc_indices = topic_to_doc_indices

    def compute_levels(self, parent_id, level, levels):
        levels[parent_id] = level
        children = self.df[self.df['Parent_ID'] == parent_id]

        for _, child in children.iterrows():
            self.compute_levels(child['Child_Left_ID'], level + 1, levels)
            self.compute_levels(child['Child_Right_ID'], level + 1, levels)

    def compute_raw_leaf_points(self, parent_id):
        if parent_id in self.raw_leaf_points_count:
            return self.raw_leaf_points_count[parent_id], self.raw_leaf_points_list[parent_id]

        children = self.df[self.df['Parent_ID'] == parent_id]

        if children.empty:
            parent_id_int = int(parent_id)
            if parent_id_int in self.topic_to_doc_indices:
                doc_indices = [idx for idx, x in enumerate(self.topic_to_doc_indices) if x == parent_id_int]
                count = len(doc_indices)
            else:
                count = 0
                doc_indices = []
            self.raw_leaf_points_count[parent_id] = count
            self.raw_leaf_points_list[parent_id] = doc_indices
            return count, doc_indices

        total_leaf_points = 0
        all_leaf_points = []

        for _, child in children.iterrows():
            left_count, left_list = self.compute_raw_leaf_points(child['Child_Left_ID'])
            right_count, right_list = self.compute_raw_leaf_points(child['Child_Right_ID'])

            total_leaf_points += left_count + right_count
            all_leaf_points.extend(left_list)
            all_leaf_points.extend(right_list)

        self.raw_leaf_points_count[parent_id] = total_leaf_points
        self.raw_leaf_points_list[parent_id] = all_leaf_points

        return total_leaf_points, all_leaf_points

    def get_levels(self):
        levels = {}
        all_child_ids = set(self.df['Child_Left_ID']).union(set(self.df['Child_Right_ID']))
        roots = self.df[~self.df['Parent_ID'].isin(all_child_ids)]
        for _, root in roots.iterrows():
            self.compute_levels(root['Parent_ID'], 0, levels)
        return levels

    def get_raw_leaf_points(self):
        roots = self.df[~self.df['Parent_ID'].isin(self.df['Child_Left_ID']) & ~self.df['Parent_ID'].isin(self.df['Child_Right_ID'])]
        for _, root in roots.iterrows():
            self.compute_raw_leaf_points(root['Parent_ID'])

        return self.raw_leaf_points_count, self.raw_leaf_points_list

def get_balanced_clusters(df, parent_id, max_points=4000):
    balanced_clusters = []
    cluster_row = df[df['Parent_ID'] == parent_id].iloc[0]
    num_points = cluster_row['num_points']

    if num_points <= max_points:
        balanced_clusters.append(cluster_row['Parent_ID'])
        return balanced_clusters

    children = df[df['Parent_ID'] == parent_id]

    for _, child in children.iterrows():
        balanced_clusters += get_balanced_clusters(df, child['Child_Left_ID'], max_points)
        balanced_clusters += get_balanced_clusters(df, child['Child_Right_ID'], max_points)

    return balanced_clusters

def assign_outliers_to_balanced_clusters(balanced_clusters_df, document_topic, probabilities):
    # Prepare a topic-cluster mapping for fast lookups
    topic_cluster_map = {}
    for _, row in balanced_clusters_df.iterrows():
        for topic in row['Topics']:
            topic_cluster_map[topic] = row['Parent_ID']

    # Initialize lists to store results
    original_indices = []
    new_clusters = []
    total_probs = []

    # Find the indices of documents that are outliers (-1)
    # outlier_indices = np.where(np.array(document_topic) == -1)[0]
    outlier_indices = np.where(np.array(document_topic) > -2)[0]

    # For each outlier, find the most probable cluster
    for idx in outlier_indices:
        topic_probs = np.array(probabilities[idx])
        cluster_indices = [topic_cluster_map.get(t, -1) for t in range(len(topic_probs))]

        # Create a DataFrame for aggregation
        df = pd.DataFrame({
            'Cluster': cluster_indices,
            'Probability': topic_probs
        })

        # Sum probabilities by cluster
        df_grouped = df.groupby('Cluster').sum()

        # Find the cluster with the maximum total probability
        best_cluster = df_grouped['Probability'].idxmax()

        # Append to lists
        original_indices.append(idx)
        new_clusters.append(best_cluster)
        total_probs.append(df_grouped.loc[best_cluster, 'Probability'])

    # Create a DataFrame for the results
    return pd.DataFrame({
        'original_index': original_indices,
        'new_cluster': new_clusters,
        'total_probability': total_probs
    })