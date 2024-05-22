import numpy as np
import pandas as pd
from typing import List, Dict
from bertopic import BERTopic
from omegaconf import DictConfig

OUTLIER_CLUSTER = -1


class ClusterHierarchyColumns:
    cluster_id = 'cluster_id'
    cluster_name = 'cluster_name'
    left_child_id = 'left_child_id'
    right_child_id = 'right_child_id'
    left_child_name = 'left_child_name'
    right_child_name = 'right_child_name'
    level = 'level'
    num_docs = 'num_docs'
    doc_list = 'doc_list'
    storylines = 'storylines'


class ClusterHierarchyService:

    def __init__(self, documents: List[str], bertopic_model: BERTopic, cfg: DictConfig, desired_clusters: int):
        self._bertopic = bertopic_model
        self.cfg = cfg
        self.hierarchy_df = self._bertopic.hierarchical_topics(docs=documents)
        self._all_child_ids = None
        self.root_cluster_id = None
        self._raw_leaf_points_count = {}
        self._raw_leaf_points_list = {}
        self.balanced_clusters = None
        self.story_cluster_map = {}
        self.desired_clusters = desired_clusters
        self.doc_limit = int(len(documents)/(desired_clusters + 1))

    def setup(self):
        self._format_hierarchy_df()
        self._get_all_child_ids()
        self._perform_validations()
        self._find_root_cluster_id()
        self._add_leaf_topics_to_hierarchy_df()

        levels = self._populate_levels(parent_cluster_id=self.root_cluster_id, parent_level=0)
        self._find_documents_in_cluster(cluster_id=self.root_cluster_id)

        self.hierarchy_df[ClusterHierarchyColumns.level] = self.hierarchy_df[ClusterHierarchyColumns.cluster_id].map(levels)
        self.hierarchy_df[ClusterHierarchyColumns.num_docs] = self.hierarchy_df[ClusterHierarchyColumns.cluster_id].map(self._raw_leaf_points_count)
        self.hierarchy_df[ClusterHierarchyColumns.doc_list] = self.hierarchy_df[ClusterHierarchyColumns.cluster_id].map(self._raw_leaf_points_list)

        self.balanced_clusters = self._get_balanced_clusters(cluster_id=self.root_cluster_id)
        self.story_cluster_map = self._map_stories_to_balanced_clusters()

    def _format_hierarchy_df(self):

        self.hierarchy_df.columns = [x.lower() for x in self.hierarchy_df.columns]
        self.hierarchy_df = self.hierarchy_df.rename(columns={'topics': ClusterHierarchyColumns.storylines,
                                                              'parent_id': ClusterHierarchyColumns.cluster_id,
                                                              'parent_name': ClusterHierarchyColumns.cluster_name,
                                                              'child_left_id': ClusterHierarchyColumns.left_child_id,
                                                              'child_right_id': ClusterHierarchyColumns.right_child_id,
                                                              'child_left_name': ClusterHierarchyColumns.left_child_name,
                                                              'child_right_name': ClusterHierarchyColumns.right_child_name
                                                              })
        self.hierarchy_df[ClusterHierarchyColumns.cluster_id] = self.hierarchy_df[ClusterHierarchyColumns.cluster_id].astype('int')
        self.hierarchy_df[ClusterHierarchyColumns.left_child_id] = self.hierarchy_df[ClusterHierarchyColumns.left_child_id].apply(lambda x: int(x) if x is not None else x)
        self.hierarchy_df[ClusterHierarchyColumns.right_child_id] = self.hierarchy_df[ClusterHierarchyColumns.right_child_id].apply(lambda x: int(x) if x is not None else x)

    def _get_all_child_ids(self):
        self._all_child_ids = set(self.hierarchy_df[ClusterHierarchyColumns.left_child_id]).union(set(self.hierarchy_df[ClusterHierarchyColumns.right_child_id]))

    def _perform_validations(self):
        # Condition 1:  Verifying that both left and right children exist of don't exist together
        condition = (self.hierarchy_df[ClusterHierarchyColumns.left_child_id].isnull() == self.hierarchy_df[ClusterHierarchyColumns.right_child_id].isnull())
        assert condition.all(), "Mismatch between child_left_id and child_right_id null values!"

        # Condition 2: each cluster_id should have a maximum of 1 row in the dataframe
        assert self.hierarchy_df.groupby(ClusterHierarchyColumns.cluster_id)[ClusterHierarchyColumns.cluster_id].count().max() <= 1, f"max children in hierarchy df is not 1"

        # Condition 3: There should only be 1 root
        num_roots = len(self.hierarchy_df[~self.hierarchy_df[ClusterHierarchyColumns.cluster_id].isin(self._all_child_ids)])
        assert num_roots == 1, f"Expecting exactly 1 root. Found {num_roots}"

        # Condition 4: topic ids are expected to be continuous from 0 to 'n'
        all_topic_ids = sorted(list(set([x for x in self._bertopic.topics_ if x != OUTLIER_CLUSTER])))
        assert all_topic_ids == list(range(len(all_topic_ids))), f"topic id validation failed. topic_ids are not from 0 to {len(all_topic_ids) - 1}"

    def _add_leaf_topics_to_hierarchy_df(self):
        leaf_topic_rows = [{ClusterHierarchyColumns.cluster_id: topic_id,
                            ClusterHierarchyColumns.cluster_name: topic_name,
                            ClusterHierarchyColumns.left_child_id: None,
                            ClusterHierarchyColumns.left_child_name: '',
                            ClusterHierarchyColumns.right_child_id: None,
                            ClusterHierarchyColumns.right_child_name: '',
                            ClusterHierarchyColumns.storylines: []} for topic_id, topic_name in self._bertopic.topic_labels_.items()]
        self.hierarchy_df = pd.concat([self.hierarchy_df, pd.DataFrame(leaf_topic_rows)], ignore_index=True)
        # self.hierarchy_df = self.hierarchy_df.convert_dtypes()
        # for col in [ClusterHierarchyColumns.cluster_id, ClusterHierarchyColumns.left_child_id, ClusterHierarchyColumns.right_child_id]:
        #     self.hierarchy_df[col] = self.hierarchy_df[col].astype('Int64')

    def _find_root_cluster_id(self):
        self.root_cluster_id = self.hierarchy_df[~self.hierarchy_df[ClusterHierarchyColumns.cluster_id].isin(self._all_child_ids)].squeeze()[ClusterHierarchyColumns.cluster_id]

    def _populate_levels(self, parent_cluster_id, parent_level):
        # notice that not all leaf clusters: stories are at the same level.
        if pd.isna(parent_cluster_id) or parent_cluster_id is None:  # Using pd.na because Nones are converted to pd.na by pandas dataframe
            return {}

        levels = {parent_cluster_id: parent_level}
        cluster_row = self.hierarchy_df[self.hierarchy_df[ClusterHierarchyColumns.cluster_id] == parent_cluster_id].squeeze()
        if not cluster_row.empty:  # We already asserted above that a cluster has a max of 1 row
            left_child_id = cluster_row[ClusterHierarchyColumns.left_child_id]
            right_child_id = cluster_row[ClusterHierarchyColumns.right_child_id]
            levels.update(self._populate_levels(left_child_id, parent_level + 1))
            levels.update(self._populate_levels(right_child_id, parent_level + 1))
        return levels

    def _find_documents_in_cluster(self, cluster_id):
        # avoid duplication computation
        if cluster_id in self._raw_leaf_points_list:
            return self._raw_leaf_points_list[cluster_id]

        cluster_row = self.hierarchy_df[self.hierarchy_df[ClusterHierarchyColumns.cluster_id] == cluster_id].squeeze()
        left_child_id = cluster_row[ClusterHierarchyColumns.left_child_id]
        right_child_id = cluster_row[ClusterHierarchyColumns.right_child_id]

        if pd.notna(left_child_id) and pd.notna(right_child_id):    # non leaf cluster: get documents within sub-clusters
            left_child_doc_list = self._find_documents_in_cluster(left_child_id)
            right_child_doc_list = self._find_documents_in_cluster(right_child_id)
            indices = left_child_doc_list + right_child_doc_list
        else:  # leaf cluster: storyline
            indices = [idx for idx, x in enumerate(self._bertopic.topics_) if x == cluster_id]

        self._raw_leaf_points_list[cluster_id] = indices
        self._raw_leaf_points_count[cluster_id] = len(indices)

        return indices

    def _get_balanced_clusters(self, cluster_id: int) -> List[int]:
        balanced_clusters = []
        cluster_row = self.hierarchy_df[self.hierarchy_df[ClusterHierarchyColumns.cluster_id] == cluster_id].squeeze()  # asserted above that only 1 per df
        # the cluster is below the doc limit or is a leaf topic - then add cluster
        # if cluster_row[ClusterHierarchyColumns.num_docs] <= self.cfg.balanced_cluster_doc_limit or pd.isna(cluster_row[ClusterHierarchyColumns.left_child_id]):
        if cluster_row[ClusterHierarchyColumns.num_docs] <= self.doc_limit or pd.isna(cluster_row[ClusterHierarchyColumns.left_child_id]):
            balanced_clusters.append(cluster_row[ClusterHierarchyColumns.cluster_id])
            return balanced_clusters
        else:
            balanced_clusters += self._get_balanced_clusters(cluster_id=cluster_row[ClusterHierarchyColumns.left_child_id])
            balanced_clusters += self._get_balanced_clusters(cluster_id=cluster_row[ClusterHierarchyColumns.right_child_id])

        return balanced_clusters

    def _map_stories_to_balanced_clusters(self) -> Dict[int, int]:
        # Prepare a topic-cluster mapping for fast lookups
        balanced_clusters_df = self.hierarchy_df[self.hierarchy_df[ClusterHierarchyColumns.cluster_id].isin(self.balanced_clusters)]
        storyline_cluster_map = {}
        for _, row in balanced_clusters_df.iterrows():
            storylines = row[ClusterHierarchyColumns.storylines]
            cluster_id = row[ClusterHierarchyColumns.cluster_id]
            if storylines:
                for storyline in storylines:
                    storyline_cluster_map[storyline] = cluster_id
            else:
                storyline_cluster_map[cluster_id] = cluster_id
        return storyline_cluster_map
