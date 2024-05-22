import os

import numpy as np
from bertopic import BERTopic

from src._validations import _validate_story_cluster_map, _validate_embedding_and_model, validate_embedding
from typing import Dict, List
from src.clustering._utils import assign_article_to_cluster
from src._utils import load_bertopic_model_from_hf, get_embedding_model_name, get_embedding_model_size
from sql.clustering.ClusteringSQL import ClusteringSQL
from sql.embeddings.EmbeddingSQL import EmbeddingSQL
from sklearn.metrics.pairwise import cosine_similarity

from src.data_models.Article import Article


class ClusterAssignmentService:

    def __init__(self, clustering_run_id, bertopic_model: BERTopic):
        self.clustering_run_id = clustering_run_id
        self.bertopic_model = bertopic_model
        # TODO: - refactor to get mapping for a generic run_id
        mapping_clustering_run_id, self.story_to_cluster = ClusteringSQL.get_story_to_cluster_mapping()
        self.embedding_model_name = get_embedding_model_name(run_id=self.clustering_run_id)
        assert mapping_clustering_run_id == clustering_run_id, f"init run_id {clustering_run_id} is different from run id  {mapping_clustering_run_id} with story cluster mapping"
        _validate_story_cluster_map(stories=self.bertopic_model.topic_labels_.keys(), story_cluster_map=self.story_to_cluster)
        self.story_embeddings = ClusteringSQL.get_all_story_embeddings()
        self.non_outlier_story_embeddings = {x: val for x, val in self.story_embeddings.items() if x != -1}
        self.embedding_size = get_embedding_model_size(run_id=self.clustering_run_id)

    @staticmethod
    def is_earnings_report_article(title):
        title = title.lower()
        return ('consolidated' in title or 'standalone' in title) and ('net sales' in title or 'net profit' in title or 'net loss' in title)

    @staticmethod
    def is_live_blog_article(url):
        return 'https://www.livemint.com/market/live-blog' in url

    def compute_save_cluster_id_for_article_id(self, article_id: str, article_text: str, article: Article):
        manual = False
        if ClusterAssignmentService.is_earnings_report_article(article.title):
            cluster_details = {'storyline_id': 1000, 'cluster_id': 142}
            manual = True
        if ClusterAssignmentService.is_live_blog_article(article.url):
            cluster_details = {'storyline_id': 1001, 'cluster_id': 143}
            manual = True
        if not manual:
            article_embeddings, emb_model_name = EmbeddingSQL.get_embedding_and_model_name_for_article_id(article_id=article_id)
            _validate_embedding_and_model(embedding=article_embeddings,
                                          expected_emb_size=self.embedding_size,
                                          actual_emb_model=emb_model_name,
                                          expected_emb_model=self.embedding_model_name)
            if os.environ.get('BERTOPIC_MODEL_TYPE') == 'full':
                cluster_details = self._get_UMAP_based_cluster_details_for_article(article_text=article_text,
                                                                                   embedding=article_embeddings)
            else:
                cluster_details = self.get_approximate_cluster_details_for_article(embedding=article_embeddings)
        ClusteringSQL.save_cluster_details_for_article_id_to_db(article_id=article_id,
                                                                article_dict=cluster_details,
                                                                clustering_run_id=self.clustering_run_id)

    def get_approximate_cluster_details_for_article(self, embedding: List[float]):
        # calculating cosine similarity for all stories except outlier
        cluster_details = {}
        sim_matrix = cosine_similarity([embedding], list(self.non_outlier_story_embeddings.values()))
        cluster_details['storyline_id'] = np.argmax(sim_matrix)  # doing -1 for the outlier
        cluster_details['cluster_id'] = self.story_to_cluster[cluster_details['storyline_id']]
        return cluster_details

    def _get_UMAP_based_cluster_details_for_article(self, article_text: str, embedding: List[float]):
        assert isinstance(article_text, str), f"document is not a string"
        # TODO: - refactor to store topic wise embeddings to db and use cosine similarity instead of bertopic
        story, probabilities = self.bertopic_model.transform(documents=[article_text],
                                                             embeddings=np.array(embedding).reshape(-1, 1).T)
        story = story[0]
        probabilities = list(probabilities[0])
        cluster_details = assign_article_to_cluster(article_story_id=story,
                                                    article_story_probs=probabilities,
                                                    story_cluster_map=self.story_to_cluster)
        return cluster_details
