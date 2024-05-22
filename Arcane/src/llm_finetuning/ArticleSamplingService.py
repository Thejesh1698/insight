import pandas as pd
import numpy as np
from sql.articles.MongoDBArticle import MongoDBArticle
from sql.PostgresDatabaseOperation import PostgresDatabaseOperation
import re

from src.data_models.Article import Article


class ArticleSamplingService:

    def __init__(self, num_articles=1000):
        self.articles_df = None
        self.source_df = None
        self.fullcat_prob = None
        self.re_weighted_fullcat_prob_df = None
        self.num_articles = num_articles
        self.shortlisted_articles = None
        self.oversampled_articles_df = None
        self.final_shortlisted_articles = None
        self.min_proportion = 0.025

    def sample_articles(self):
        self._load_all_articles()
        self._load_article_category_details()
        self._calculate_category_representation()
        self._shortlist_articles()
        self._reduce_inequality()
        self._format_shortlisted_articles()

    def _load_all_articles(self):
        all_documents = MongoDBArticle.fetch_all_articles(limit=None)
        self.articles_df = pd.DataFrame(all_documents)
        with PostgresDatabaseOperation() as cursor:
            sql = 'SELECT source_id, source_name FROM source_id_characteristics'
            cursor.execute(sql)
            results = cursor.fetchall()
        self.source_df = pd.DataFrame(results, columns=['source_id', 'source_name'])
        self.articles_df = pd.merge(self.articles_df, self.source_df, how='left', on='source_id')

    def _load_article_category_details(self):
        self.articles_df[['cat', 'subcat']] = self.articles_df.apply(ArticleSamplingService._extract_category_subcategory, axis=1, result_type='expand')
        invalid_cats = self.articles_df[self.articles_df.groupby('cat')['cat'].transform('count') == 1].cat.unique()
        invalid_subcats = self.articles_df[self.articles_df.groupby('subcat')['subcat'].transform('count') == 1].subcat.unique()
        self.articles_df.loc[self.articles_df.cat.isin(invalid_cats), 'cat'] = ''
        self.articles_df.loc[self.articles_df.subcat.isin(invalid_subcats), 'subcat'] = ''
        self.articles_df['fullcat'] = self.articles_df['source_name'] + '-' + self.articles_df['cat'] + '-' + self.articles_df['subcat']

    def _calculate_category_representation(self):
        self.fullcat_prob = self.articles_df.groupby('fullcat')['article_id'].count() / len(self.articles_df)
        re_weighted_fullcat_prob = np.power(self.fullcat_prob, -0.5) / np.sum(np.power(self.fullcat_prob, -0.5))
        self.re_weighted_fullcat_prob_df = pd.DataFrame(re_weighted_fullcat_prob).rename(columns={'article_id': 'proportion'}).reset_index()

    def _shortlist_articles(self):
        for col in ['proportion', 'scaled_proportion', 'prob', 'is_selected']:
            if col in self.articles_df.columns:
                self.articles_df = self.articles_df.drop(columns=[col])
        self.articles_df = pd.merge(self.articles_df, self.re_weighted_fullcat_prob_df, how='left')
        base_level = np.sum(self.articles_df['proportion'])
        self.articles_df['scaled_proportion'] = self.articles_df['proportion'] * (self.num_articles / base_level)
        self.articles_df['prob'] = [np.random.rand() for i in range(len(self.articles_df))]
        self.articles_df['is_selected'] = self.articles_df['prob'] < self.articles_df['scaled_proportion']
        self.articles_df[self.articles_df.is_selected == 1].groupby('source_name')['is_selected'].sum().nlargest(100)
        self.shortlisted_articles = self.articles_df[self.articles_df.is_selected == True]
        self.shortlisted_articles = self.shortlisted_articles.sample(frac=1)

    def _reduce_inequality(self):
        representation_cutoff = int(self.min_proportion * self.num_articles)
        under_represented_sources = self.articles_df[self.articles_df.is_selected == 1].groupby('source_name').filter(lambda x: len(x) < representation_cutoff)[
            'source_name'].unique()
        cur_representation = self.articles_df[self.articles_df.is_selected == 1].groupby('source_name').filter(lambda x: len(x) < representation_cutoff).groupby('source_name')[
            'source_name'].count()
        oversampling_requirement = representation_cutoff - cur_representation
        self.oversampled_articles_df = pd.DataFrame()
        # Loop through each group, sample, and append to the sampled_df.
        for group, num_samples in dict(oversampling_requirement).items():
            group_sample = self.articles_df[self.articles_df['source_name'] == group].sample(n=min(len(self.articles_df[self.articles_df['source_name'] == group]), num_samples))
            self.oversampled_articles_df = pd.concat([self.oversampled_articles_df, group_sample])
        self.final_shortlisted_articles = pd.concat([self.shortlisted_articles, self.oversampled_articles_df])
        self.final_shortlisted_articles = self.final_shortlisted_articles.drop_duplicates('article_id')

    def _format_shortlisted_articles(self):
        self.final_shortlisted_articles['full_content'] = self.final_shortlisted_articles.apply(lambda x: Article._generate_full_content(x['title'], x['cleaned_text']), axis=1)
        self.final_shortlisted_articles = self.final_shortlisted_articles.drop(['_id', '_class', 'image_url', 'is_premium_article', 'last_updated_time', 'reactions', 'content_type', 'comments_info'],
                                                                               axis=1)

    @staticmethod
    def _extract_category_subcategory(row):
        # 20 and 25 identified based on iterative analysis
        ignore_first_level = ['money-control']
        subcat_sources = ['live-mint', 'economic-times', 'cnbc-tv-18']
        cat_sources = ['navi', 'zerodha-varsity', 'wint-wealth', 'investopedia', 'groww', 'business-world', 'bq-prime']
        source = row['source_name']
        x = row['url']
        if source in cat_sources:
            cat_url = re.split('.com/|.in/', x)[1]
            cat = cat_url.split('/')[0]
            if len(cat) < 20:
                return cat, ''
            else:
                return '', ''
        elif source in subcat_sources:
            cat_url = re.split('.com/|.in/', x)[1]
            cat = cat_url.split('/')[0]
            sub_cat = cat_url.split('/')[1]
            if len(sub_cat) < 25:
                return cat, sub_cat
            else:
                return cat, ''
        elif source in ignore_first_level:
            cat_url = re.split('.com/|.in/', x)[1]
            cat_split = cat_url.split('/')
            cat = cat_split[1]
            if len(cat_split) > 2 and len(cat_split[2]) < 25:
                sub_cat = cat_split[2]
                return cat, sub_cat
            else:
                return cat, ''
        else:
            return '', ''
