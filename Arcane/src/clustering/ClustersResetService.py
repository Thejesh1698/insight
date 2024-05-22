import logging
import time
from copy import deepcopy

import numpy as np
import pandas as pd
from bertopic.backend._sentencetransformers import SentenceTransformerBackend
from hydra import initialize, compose
from omegaconf import DictConfig
from typing import List, Dict
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer

from sql.articles.MongoDBArticle import MongoDBArticle
from src.articles.ArticleService import ArticleService
from src.clustering._utils import assign_article_to_cluster
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from src.clustering.ClusterHierarchyService import ClusterHierarchyService
from src.clustering._utils import generate_unique_run_id
from src._utils import save_bertopic_model_to_hf, save_bertopic_model_to_s3, save_file_to_s3_model_folder
from sql.clustering.ClusteringSQL import ClusteringSQL
from sql.embeddings.EmbeddingSQL import EmbeddingSQL
from src.topics.TopicClusterMapping import TopicClusterMapping

OUTLIER = -1


# DONE: - clustering assignment stand alone application
# TODO: - add ability to merge topics based on cosine similarity threshold and document threshold
# DONE: - migrate to using article ids instead of loading from parquet or file
# DONE: - save article to storyline and cluster mapping
# TODO: - compare the cluster names using just title vs title + content
# TODO: - ensure that article id index is maintained across places
class ClustersResetService:
    def __init__(self,
                 cfg: DictConfig,
                 category: str = None,
                 random_state: int = None,
                 desired_clusters=4
                 ):
        logging.info('cluster reset service has been called')
        self.cfg = cfg
        self.random_state = random_state

        self.embeddings = None
        self.all_article_ids = None
        self.model_name = None
        self.bertopic_model = None
        self.embeddings_mapping = None
        self.documents = None
        self.category = category
        self.desired_clusters = desired_clusters
        if not self.category:
            self._load_all_article_embedding_data()
        else:
            self._load_article_embedding_data()
        self.article_documents = self._get_documents_for_articles()
        self._ignore_null_documents()

        self.bertopic_model = self._fit_bertopic_model_to_documents()
        #
        self.cluster_hierarchy = ClusterHierarchyService(bertopic_model=self.bertopic_model, documents=self.documents, cfg=cfg, desired_clusters=self.desired_clusters)
        self.cluster_hierarchy.setup()
        self.article_story_cluster_map = self.assign_articles_to_clusters()

        # saving to db
        self.run_id = generate_unique_run_id()
        self._save_clustering_details_to_s3()
        logging.info('clustering details saved to s3')
        save_bertopic_model_to_s3(model=self.bertopic_model, run_id=self.run_id)
        logging.info('bertopic model saved to s3')
        save_bertopic_model_to_hf(model=self.bertopic_model, is_dev=True, run_id=self.run_id)
        logging.info("docs assigned to balanced clusters")
        self._trigger_topic_preferences_recalculation()

    def _load_all_article_embedding_data(self):
        # self.article_embeddings_df = EmbeddingSQL.get_all_embeddings()
        self.embeddings_mapping, model_names = EmbeddingSQL.get_all_relevant_embeddings()
        logging.info(f'fetched all relevant embeddings for {len(self.embeddings_mapping)} articles')
        # self.embeddings_mapping = {row['article_id']: row['embedding'] for i, row in self.article_embeddings_df.iterrows()}
        assert len(model_names) == 1, f"expecting only 1 embedding model for embeddings. {len(model_names)} found"
        # assert self.article_embeddings_df['model_name'].nunique() == 1, (f"expecting only 1 embedding model for embeddings. "
        #                                                                  f"{len(self.article_embeddings_df['model_name'].nunique())} found")
        # self.model_name = self.article_embeddings_df['model_name'].unique()[0]
        self.model_name = model_names[0]

    def _load_article_embedding_data(self):
        # self.article_embeddings_df = EmbeddingSQL.get_all_embeddings()
        self.embeddings_mapping, model_names = EmbeddingSQL.get_category_embeddings(category=self.category)
        logging.info(f'fetched all relevant embeddings for {len(self.embeddings_mapping)} articles')
        # self.embeddings_mapping = {row['article_id']: row['embedding'] for i, row in self.article_embeddings_df.iterrows()}
        assert len(model_names) == 1, f"expecting only 1 embedding model for embeddings. {len(model_names)} found"
        # assert self.article_embeddings_df['model_name'].nunique() == 1, (f"expecting only 1 embedding model for embeddings. "
        #                                                                  f"{len(self.article_embeddings_df['model_name'].nunique())} found")
        # self.model_name = self.article_embeddings_df['model_name'].unique()[0]
        self.model_name = model_names[0]

    def _get_documents_for_articles(self):
        # TODO: - move this to mongo
        article_documents = {}
        emb_articles = list(self.embeddings_mapping.keys())
        logging.info(f'proceeding to fetch article details for {len(emb_articles)} articles')
        article_metadata = MongoDBArticle.fetch_documents_by_ids(string_ids=emb_articles)
        article_metadata = {str(x['_id']): x for x in article_metadata}
        valid_article_ids = list(self.embeddings_mapping.keys())
        logging.info('article details fetched')
        for article in valid_article_ids:
            if article in article_metadata:
                article_documents[article] = article_metadata[article]['title']
        return article_documents

    def _ignore_null_documents(self):
        self.embeddings = []
        self.documents = []
        self.all_article_ids = []
        null_articles = []
        for article_id, article_document in self.article_documents.items():
            if article_document is None or article_document == '':
                null_articles.append(article_id)
            else:
                self.embeddings.append(self.embeddings_mapping[article_id])
                self.documents.append(self.article_documents[article_id])
                self.all_article_ids.append(article_id)
        for article_id in null_articles:
            self.embeddings_mapping.pop(article_id)
            self.article_documents.pop(article_id)

        self.embeddings = np.array(self.embeddings)
        self.documents = np.array(self.documents)

    def _fit_bertopic_model_to_documents(self):
        custom_umap_model = UMAP(n_neighbors=self.cfg.umap_n_neighbors,
                                 n_components=self.cfg.umap_n_components,
                                 metric='cosine',
                                 random_state=self.random_state)
        num_docs = len(self.documents)
        self.min_cluster_size = int(num_docs)/(3 * self.desired_clusters)
        self.min_samples = int(num_docs)/(4 * self.desired_clusters)
        # custom_hdbscan_model = HDBSCAN(min_cluster_size=self.cfg.hdbscan_min_cluster_size,
        #                                min_samples=self.cfg.hdbscan_min_samples,
        #                                metric='cosine',
        #                                prediction_data=True)
        custom_hdbscan_model = HDBSCAN(min_cluster_size=self.min_cluster_size,
                                       min_samples=self.min_samples,
                                       metric='cosine',
                                       prediction_data=True)
        vectorizer_model = CountVectorizer(stop_words="english",
                                           max_df=0.7,
                                           ngram_range=(1, 2))
        bertopic_model = BERTopic(umap_model=custom_umap_model,
                                  hdbscan_model=custom_hdbscan_model,
                                  vectorizer_model=vectorizer_model,
                                  embedding_model=SentenceTransformer(self.model_name),
                                  verbose=True,
                                  calculate_probabilities=True)
        logging.info("bertopic model instantiated")

        bertopic_model.fit_transform(documents=self.documents, embeddings=self.embeddings)
        bertopic_model.generate_topic_labels(nr_words=5, separator=", ")
        logging.info(f"model fit to documents")
        return bertopic_model

    def assign_articles_to_clusters(self) -> Dict[int, dict]:
        article_story_mapping = self.bertopic_model.topics_
        article_story_probs = self.bertopic_model.probabilities_

        article_story_cluster_mapping = {}
        for article_idx, story_id in enumerate(article_story_mapping):
            article_dict = assign_article_to_cluster(article_story_id=story_id,
                                                     article_story_probs=np.array(article_story_probs[article_idx]),
                                                     story_cluster_map=self.cluster_hierarchy.story_cluster_map)

            article_id = self.all_article_ids[article_idx]
            article_story_cluster_mapping[article_id] = article_dict

        return article_story_cluster_mapping

    def _save_clustering_details_to_s3(self):
        # run details
        # self._save_clustering_run_details_to_db()
        save_file_to_s3_model_folder(run_id=self.run_id, data=self.article_story_cluster_map, filename='article_story_cluster_mapping', filetype='.json')
        # saving article to cluster mapping
        # TODO: - refactor code everywhere to use the updated terminology.
        renamed_hierarchy_df = deepcopy(self.cluster_hierarchy.hierarchy_df)
        renamed_hierarchy_df = renamed_hierarchy_df.rename(columns={'cluster_id': 'parent_id', 'cluster_name': 'parent_name', 'storylines': 'child_storyline_list',
                                                                    'left_child_id': 'child_left_id', 'left_child_name': 'child_left_name',
                                                                    'right_child_id': 'child_right_id', 'right_child_name': 'child_right_name'})
        save_file_to_s3_model_folder(run_id=self.run_id, data=renamed_hierarchy_df, filename='cluster_hierarchy', filetype='.csv')
        save_file_to_s3_model_folder(run_id=self.run_id, data=self.cluster_hierarchy.story_cluster_map, filename='story_cluster_mapping', filetype='.json')
        story_embeddings_dict = {}
        for i in range(-1, len(self.bertopic_model.topic_embeddings_) - 1):
            story_embeddings_dict[i] = [float(x) for x in list(self.bertopic_model.topic_embeddings_[i + 1])]
        save_file_to_s3_model_folder(run_id=self.run_id, data=story_embeddings_dict, filename='story_embeddings', filetype='.json')

    def _save_clustering_details_to_db(self):
        # run details
        self._save_clustering_run_details_to_db()
        # saving article to cluster mapping
        ClusteringSQL.save_article_story_cluster_mapping(article_story_cluster_mapping=self.article_story_cluster_map,
                                                         clustering_run_id=self.run_id)
        # hierarchy
        # TODO: - refactor code everywhere to use the updated terminology.
        renamed_hierarchy_df = deepcopy(self.cluster_hierarchy.hierarchy_df)
        renamed_hierarchy_df = renamed_hierarchy_df.rename(columns={'cluster_id': 'parent_id', 'cluster_name': 'parent_name', 'storylines': 'child_storyline_list',
                                                                    'left_child_id': 'child_left_id', 'left_child_name': 'child_left_name',
                                                                    'right_child_id': 'child_right_id', 'right_child_name': 'child_right_name'})
        ClusteringSQL.insert_cluster_hierarchy(cluster_hierarchy_df=renamed_hierarchy_df,
                                               clustering_run_id=self.run_id)
        # story to cluster mapping
        ClusteringSQL.insert_storyline_to_cluster_mapping(story_to_cluster_mapping=self.cluster_hierarchy.story_cluster_map,
                                                          clustering_run_id=self.run_id)

        ClusteringSQL.insert_story_embeddings(story_embeddings=self.bertopic_model.topic_embeddings_,
                                              clustering_run_id=self.run_id)

    def _get_embedding_size(self):
        # Assert that it is of type SentenceTransformerBackend
        assert isinstance(self.bertopic_model.embedding_model, SentenceTransformerBackend), "The embedding model in the bertopic is not of type SentenceTransformerBackend"
        sentence_transformer_backend = self.bertopic_model.embedding_model
        return len(sentence_transformer_backend.embed_words('insight'))

    def _save_clustering_run_details_to_db(self):
        run_details_dict = dict(self.cfg)
        run_details_dict['num_docs'] = len(self.article_documents)
        run_details_dict['random_state'] = self.random_state
        run_details_dict['run_time'] = time.time()
        run_details_dict['run_id'] = self.run_id
        run_details_dict['embedding_model_name'] = self.model_name
        run_details_dict['embedding_size'] = self._get_embedding_size()

        ClusteringSQL.insert_clustering_run_details(clustering_run_config=run_details_dict,
                                                    clustering_run_id=self.run_id)

    def _trigger_topic_preferences_recalculation(self):
        with initialize(config_path="../../conf"):
            # Compose the configuration
            topic_cfg = compose(config_name="TopicClusterMapping.yaml")
        topic_cluster_mapping = TopicClusterMapping(clustering_run_id=self.run_id, bertopic_model=self.bertopic_model, cfg=topic_cfg)
        topic_cluster_mapping.recompute_preferences_for_all_topics()
