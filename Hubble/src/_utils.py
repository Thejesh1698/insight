from typing import Union
import numpy as np
import re
import pandas as pd
from datetime import datetime, timezone

from src.Article import Article


def decay_sigmoid_function(n):
    return 0.33 + (0.67 / (1 + np.exp((3 * np.log10(n)) - 3)))


def clean_search_query(search_query: str) -> str:
    # removing new line symbol
    search_query = search_query.replace('\n', '')
    search_query = search_query.replace('\t', '')
    search_query = search_query.strip()
    search_query = search_query.lower()
    search_query = re.sub(r"[^a-zA-Z0-9 ]", "", search_query)  # removing characters which are not part of alphabets, numbers, space
    search_query = search_query.replace('  ', ' ')  # replace double space with single
    search_query = search_query[:140]  # limit till the first 140 characters
    return search_query


def compute_publication_decay_time(num_days_ago: int):
    if num_days_ago <= 0:
        return 1.0
    elif num_days_ago > 120:
        return 0.34
    else:
        return decay_sigmoid_function(num_days_ago)


def format_published_time_df(published_time_df, max_published_date=None):
    published_time_df['published_time'] = pd.to_datetime(published_time_df['published_time'], utc=True)
    if not max_published_date:
        today_reference = datetime.today().replace(tzinfo=timezone.utc)
    else:
        today_reference = pd.to_datetime(max_published_date, utc=True)
    # published_time_df['num_days_ago'] = (today_reference - published_time_df['published_time']).dt.days
    published_time_df['num_days_ago'] = (today_reference - published_time_df['published_time']).dt.days
    return published_time_df


def create_recency_score_df(articles: [Article], max_published_date=None):
    published_time_df = pd.DataFrame([(x.article_id, x.published_time) for x in articles], columns=['article_id', 'published_time'])
    published_time_df = format_published_time_df(published_time_df=published_time_df, max_published_date=max_published_date)
    published_time_df['recency_score'] = [compute_publication_decay_time(x) for x in published_time_df['num_days_ago']]
    return published_time_df


def calc_recency_weighted_relevance(relevance_df, recency_df, recency_importance='medium', return_n=250):
    max_relevance_score = relevance_df['score'].max()
    relevance_df['scaled_score'] = relevance_df['score']/max_relevance_score
    recency_weight = 0.1
    if recency_importance.lower() == 'low':
        recency_weight = 0.1
    elif recency_importance.lower() == 'high':
        recency_weight = 0.25
    recency_weighted_scores_df = pd.merge(relevance_df, recency_df, how='left', on='article_id')
    relevance_weight = 1 - recency_weight
    recency_weighted_scores_df['weighted_score'] = relevance_weight * recency_weighted_scores_df['scaled_score'] + recency_weight * recency_weighted_scores_df['recency_score']
    recency_weighted_scores_df = recency_weighted_scores_df.nlargest(return_n, 'weighted_score')
    return recency_weighted_scores_df


def convert_dates_to_readable_format(dt):
    # Sample datetime string in the format '%Y-%m-%dT%H:%M:%S'
    try:
        datetime_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S%z')
    except:
        datetime_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
    return datetime_obj.strftime('%d %B %Y')


'''
total_template_tokens = 648
date_tokens = len(tokenizer.encode('12 February 2024'))
article_content_tokens = 896
search_query_tokens = 48
output_limit = 524
total_limit = 4096
num_articles = 3
buffer = 24
title_limit = (total_limit - (total_template_tokens + buffer + search_query_tokens + (date_tokens + article_content_tokens) * num_articles + output_limit))/num_articles
title_limit=45
'''

