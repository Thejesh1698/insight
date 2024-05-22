import numpy as np
import pandas as pd
from datetime import datetime
from sql.candidates.CandidateSQL import CandidateSQL


# TODO: - evaluate if coef as a parameter is needed or a common one works for both candidate and article selection
def apply_article_pref_decay_by_feed_date(df, decay_coef=1.0) -> pd.DataFrame:
    df['feed_date'] = pd.to_datetime(df['feed_date'])
    today = datetime.today()
    df['days_ago'] = (df['feed_date'] - today).dt.days
    # TODO: - precompute and keep
    df['decay'] = decay_coef ** df['days_ago']
    return df


def get_time_decay_article_priors_for_all_interacted_articles() -> pd.DataFrame:
    all_article_prior_df = CandidateSQL.get_day_wise_article_a_b()
    all_article_prior_df = apply_article_pref_decay_by_feed_date(df=all_article_prior_df, decay_coef=1.25)
    all_article_prior_df['ah'] = all_article_prior_df['a'] * all_article_prior_df['decay']
    all_article_prior_df['bh'] = all_article_prior_df['b'] * all_article_prior_df['decay']
    all_article_prior_df = all_article_prior_df.groupby('article_id')[['a', 'b', 'ah', 'bh']].sum().reset_index()
    all_article_prior_df = all_article_prior_df.rename(columns={'a': 'a_all', 'b': 'b_all'})
    return all_article_prior_df


def get_prior_for_popularity(article_attributes):
    valid_granular_scores = True
    # checking if all the scores exist and are float values
    total_sum = 0
    for att in ['final_reader_interest_score', 'final_headline_effectiveness_score', 'final_event_novelty_score', 'final_emotional_impact_score']:
        if att in article_attributes:
            try:
                total_sum += float(article_attributes[att])
            except:     # if key exists, but not a floatable value, then use fallback
                valid_granular_scores = False
                break
        else:       # if key doesn't exist, then use fallback
            valid_granular_scores = False
            break
    # if all scores exist, then 4 times sum of individual values
    if valid_granular_scores:
        return int(round(total_sum * 4))
    # else use popularity flag
    else:
        mapping = {'niche': 1, 'moderately_popular': 5, 'breaking_news': 15}
        return mapping.get(article_attributes['expected_popularity'], 1)


def is_candidate(attributes_dict):
    ONE_WEEK_IN_HOURS = 168
    validity = attributes_dict.get('validity_in_hours', 168)
    if validity < 0:
        validity = 365 * 24
    if pd.isna(attributes_dict.get('financial_news')) or np.isnan(attributes_dict.get('financial_news')) or attributes_dict.get('financial_news') is None:
        return attributes_dict['hours_since_publication'] <= ONE_WEEK_IN_HOURS
    else:
        return attributes_dict['financial_news'] and attributes_dict['relevant_for_india'] and attributes_dict['hours_since_publication'] < validity
