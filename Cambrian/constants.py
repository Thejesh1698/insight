import enum


SUMMARY_WEIGHTAGE = 0.5
INTERACTIONS_CUTOFF_DATE = '2024-02-27'
INTERACTIONS_EXCLUSION_USERS = '98'
NON_FIN_CLUSTER_ID = 145


class ContentType(enum.Enum):
    article = 'ARTICLE'
    podcast_episode = 'PODCAST_EPISODE'


class SourceType(enum.Enum):
    article = 'ARTICLE'
    podcast = 'PODCAST'

