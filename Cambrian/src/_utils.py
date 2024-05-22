import numpy as np
import pandas as pd
from datetime import datetime
from sql.ArticleSelectionSQL import ArticleSelectionSQL
from constants import SourceType, ContentType


def apply_user_pref_decay_by_feed_date(df):
    df['feed_date'] = pd.to_datetime(df['feed_date'])
    today = datetime.today()
    df['weeks_ago'] = (df['feed_date'] - today).dt.days // 7
    # TODO: - precompute and keep
    df['decay'] = 1.05 ** df['weeks_ago']
    return df


def decay_by_days_approximate(num_days):
    # linear approximation of sigmoid function - return 0.34 + (0.66/(1+np.exp(np.log(days + 0.00001)-3)))
    return 0.34 + (0.66 / (1 + 0.05 * num_days))


# TODO: - evaluate if coef as a parameter is needed or a common one works for both candidate and article selection
def apply_article_pref_decay_by_feed_date(df, decay_coef=1.0) -> pd.DataFrame:
    df['feed_date'] = pd.to_datetime(df['feed_date'])
    today = datetime.today()
    df['days_ago'] = (df['feed_date'] - today).dt.days
    # TODO: - precompute and keep
    df['decay'] = decay_coef ** df['days_ago']
    return df


def get_popularity_priors_for_candidates(content_type):
    if content_type == SourceType.podcast.value:
        candidate_priors = ArticleSelectionSQL.get_day_wise_candidate_article_ab(content_type=ContentType.podcast_episode.value)
    else:
        candidate_priors = ArticleSelectionSQL.get_day_wise_candidate_article_ab(content_type=content_type)
    candidate_priors['activity_date'] = pd.to_datetime(candidate_priors['activity_date'])
    candidate_priors['published_time'] = pd.to_datetime(candidate_priors['published_time'])

    candidate_priors['days_since_activity'] = (datetime.today() - candidate_priors['activity_date']).dt.days
    # TODO: - ideally the decay should also be different types
    candidate_priors['activity_decay'] = decay_by_days_approximate(candidate_priors['days_since_activity'])
    candidate_priors['hours_since_publication'] = (datetime.today() - candidate_priors['published_time'])/np.timedelta64(1, 'h')

    # We decay the past interactions to give more weightage to the latest ones
    # candidate_priors['feed_a'] = candidate_priors['feed_a'] * candidate_priors['activity_decay']
    # candidate_priors['feed_summary_a'] = candidate_priors['feed_summary_a'] * candidate_priors['activity_decay']
    candidate_priors['total_feed_a'] = candidate_priors['total_feed_a'].astype(float)
    candidate_priors['total_search_a'] = candidate_priors['total_search_a'].astype(float)
    candidate_priors['total_feed_a'] = candidate_priors['total_feed_a'] * candidate_priors['activity_decay']
    candidate_priors['total_search_a'] = candidate_priors['total_search_a'] * candidate_priors['activity_decay']
    candidate_priors['feed_b'] = candidate_priors['feed_b'] * candidate_priors['activity_decay']
    # candidate_priors['search_a'] = candidate_priors['search_a'] * candidate_priors['activity_decay']
    # candidate_priors['search_summary_a'] = candidate_priors['search_summary_a'] * candidate_priors['activity_decay']
    # candidate_priors['search_b'] = candidate_priors['search_b'] * candidate_priors['activity_decay']
    # We don't decay the pessimistic priors
    # TODO: - standardize the default prior
    default_b = 10
    candidate_priors = candidate_priors.fillna({'total_feed_a': 0, 'total_search_a': 0, 'feed_b': 0, 'search_b': 0, 'prior_a': 1, 'prior_b': default_b})
    # TODO: - correction of of search article CTR vs feed article CTR
    # candidate_priors['combined_feed_a'] = max(candidate_priors['feed_a'], 0.5 * candidate_priors['feed_summary_a'])
    # candidate_priors['combined_search_a'] = max(candidate_priors['search_a'], 0.5 * candidate_priors['search_summary_a'])
    candidate_priors['article_a'] = candidate_priors['total_feed_a'] + candidate_priors['total_search_a']
    candidate_priors['article_b'] = candidate_priors['feed_b']  # search not clicks not penalised because of search summary

    if content_type == SourceType.podcast.value:
        # in case of podcast, take the most recent publication for recency and most frequent cluster for cluster_id
        candidate_priors = candidate_priors.groupby(['source_id', 'cluster_id']).agg(
            {'hours_since_publication': 'min', 'article_id': 'count', 'article_a': 'sum', 'article_b': 'sum', 'prior_a': 'mean', 'prior_b': 'mean'}).reset_index()
        # Corrected code
        idx = candidate_priors.groupby(['source_id'])['article_id'].idxmax()
        candidate_priors = candidate_priors.loc[idx].reset_index(drop=True)
        # candidate_priors = candidate_priors.groupby(['source_id']).agg(
        #     {'hours_since_publication': 'min', 'article_id': 'max', 'article_a': 'sum', 'article_b': 'sum', 'prior_a': 'mean', 'prior_b': 'mean'}).reset_index()
        # candidate_priors = candidate_priors.rename(columns = {'article_id': 'cluster_id'})
    else:
        candidate_priors = candidate_priors.groupby(['article_id', 'source_id', 'hours_since_publication', 'cluster_id']).agg(
            {'article_a': 'sum', 'article_b': 'sum', 'prior_a': 'mean', 'prior_b': 'mean'}).reset_index()

    candidate_priors['article_a'] = candidate_priors['article_a'] + candidate_priors['prior_a']
    candidate_priors['article_b'] = candidate_priors['article_b'] + candidate_priors['prior_b']
    return candidate_priors


def get_user_cluster_implicit_priors(user_id):
    cluster_day_priors = ArticleSelectionSQL.get_user_day_wise_cluster_activity_a_b(user_id)
    cluster_day_priors['activity_date'] = pd.to_datetime(cluster_day_priors['activity_date'])
    cluster_day_priors['days_since_activity'] = (datetime.today() - cluster_day_priors['activity_date']).dt.days
    cluster_day_priors['activity_decay'] = decay_by_days_approximate(cluster_day_priors['days_since_activity'])

    # cluster_day_priors['feed_a'] = cluster_day_priors['feed_a'] * cluster_day_priors['activity_decay']
    # cluster_day_priors['feed_summary_a'] = cluster_day_priors['feed_a'] * cluster_day_priors['feed_summary_a']
    cluster_day_priors['total_feed_a'] = cluster_day_priors['total_feed_a'].astype(float)
    cluster_day_priors['total_search_a'] = cluster_day_priors['total_search_a'].astype(float)
    cluster_day_priors['total_feed_a'] = cluster_day_priors['total_feed_a'] * cluster_day_priors['activity_decay']
    cluster_day_priors['total_search_a'] = cluster_day_priors['total_search_a'] * cluster_day_priors['activity_decay']
    cluster_day_priors['feed_b'] = cluster_day_priors['feed_b'] * cluster_day_priors['activity_decay']
    # cluster_day_priors['search_a'] = cluster_day_priors['search_a'] * cluster_day_priors['activity_decay']
    # cluster_day_priors['search_summary_a'] = cluster_day_priors['feed_a'] * cluster_day_priors['search_summary_a']
    # cluster_day_priors['search_b'] = cluster_day_priors['search_b'] * cluster_day_priors['activity_decay']

    cluster_day_priors = cluster_day_priors.fillna({'total_feed_a': 0, 'total_search_a': 0, 'feed_b': 0, 'search_b': 0})

    cluster_day_priors['implicit_a'] = cluster_day_priors['total_feed_a'] + cluster_day_priors['total_search_a']
    cluster_day_priors['implicit_b'] = cluster_day_priors['feed_b']

    cluster_implicit_priors = cluster_day_priors.groupby(['cluster_id'])[['implicit_a', 'implicit_b']].sum().reset_index()
    return cluster_implicit_priors


def get_time_decay_article_priors_for_all_interacted_articles() -> pd.DataFrame:
    all_article_prior_df = ArticleSelectionSQL.get_day_wise_article_a_b()
    all_article_prior_df = apply_article_pref_decay_by_feed_date(df=all_article_prior_df, decay_coef=1.25)
    all_article_prior_df['ah'] = all_article_prior_df['a'] * all_article_prior_df['decay']
    all_article_prior_df['bh'] = all_article_prior_df['b'] * all_article_prior_df['decay']
    all_article_prior_df = all_article_prior_df.groupby('article_id')[['a', 'b', 'ah', 'bh']].sum().reset_index()
    all_article_prior_df = all_article_prior_df.rename(columns={'a': 'a_all', 'b': 'b_all'})
    return all_article_prior_df
