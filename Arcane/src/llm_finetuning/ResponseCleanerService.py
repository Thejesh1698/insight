import re

import pandas as pd
import json
from copy import deepcopy
from constants import EMOJIS

expected_keys = ['summary',
                 'summary_critique',
                 'improved_summary',
                 'top_queries',
                 'indian_or_international',
                 'business_or_financial_article',
                 'relevant_for_indians',
                 'category',
                 'article_interest_duration_evaluation',
                 'article_interest_duration',
                 'popularity_evaluation',
                 'popularity_evaluation_critique',
                 'final_reader_interest_score',
                 'final_headline_effectiveness_score',
                 'final_event_novelty_score',
                 'final_emotional_impact_score',
                 'improved_headline',
                 'article_type',
                 'article_sentiment']


class ResponseCleanerService:

    def __init__(self, response_file_path, original_data_file_path, cleaned_path=None):
        self.response_file_path = response_file_path
        self.original_data_file_path = original_data_file_path
        if not cleaned_path:
            self.cleaned_path = self.response_file_path.split('.csv')[0] + '_cleaned.csv'
        else:
            self.cleaned_path = cleaned_path
        self.response_df = None
        self.attributes_df = None
        self.cleaned_attributes_intermediate = None
        self.missing_emoji_texts = []
        self.cleaned_attributes_final = {}
        self.cleaned_attributes_df = None

    def clean_responses(self):
        self._load_response_df()
        self._create_attributes_df()
        self._clean_attributes_df()
        self._create_cleaned_attributes()
        self._save_cleaned_attributes_to_csv()

    def _load_response_df(self):
        self.response_df = pd.read_csv(self.response_file_path, header=None)
        self.response_df = self.response_df.drop(columns={0, 8})
        self.response_df = self.response_df.rename(
            columns={1: 'article_id', 2: 'system_prompt', 3: 'user_prompt', 4: 'model', 5: 'attributes', 6: 'input_tokens', 7: 'output_tokens'})

    def _create_attributes_df(self):
        all_attributes = []
        for row in self.response_df.itertuples():
            att = deepcopy(row.attributes)
            try:
                cur_att = json.loads(att)
                cur_att['article_id'] = row.article_id
                cur_att['user_prompt'] = row.user_prompt
                all_attributes.append(cur_att)
            except:
                print(row.article_id)
                # cur_att['article_id'] = row.article_id
                # all_attributes.append(cur_att)
        self.attributes_df = pd.DataFrame.from_records(all_attributes)

    def _create_cleaned_attributes(self):
        self.cleaned_attributes_intermediate = self.attributes_df[self.attributes_df['is_valid_response'] == True].to_dict('records')
        for attribute in self.cleaned_attributes_intermediate:
            attribute['improved_summary'] = attribute['cleaned_summary']
            attribute['summary'] = attribute['cleaned_first_summary']
            self.cleaned_attributes_final[attribute['article_id']] = json.dumps({k: attribute[k] for k in expected_keys})

    def _save_cleaned_attributes_to_csv(self):
        self.cleaned_attributes_df = pd.DataFrame.from_dict(self.cleaned_attributes_final, orient='index').reset_index().rename(
            columns={'index': 'article_id', 0: 'cleaned_attributes'})
        self.cleaned_attributes_df = pd.merge(self.cleaned_attributes_df, self.response_df, how='left', on='article_id')
        self.data_df = pd.read_csv(self.original_data_file_path)
        self.cleaned_attributes_df = pd.merge(self.cleaned_attributes_df, self.data_df[['article_id', 'full_content']], how='left', on='article_id')
        self.cleaned_attributes_df.to_csv(self.cleaned_path, index=False)

    def _clean_attributes_df(self):
        self.attributes_df['category'] = self.attributes_df['category'].apply(lambda x: ResponseCleanerService.fix_category(x))
        self.attributes_df['indian_or_international'] = self.attributes_df['indian_or_international'].apply(lambda x: ResponseCleanerService.fix_india_flag(x))
        self.attributes_df['business_or_financial_article'] = self.attributes_df['business_or_financial_article'].apply(lambda x: ResponseCleanerService.fix_bool_flag(x))
        self.attributes_df['relevant_for_indians'] = self.attributes_df['relevant_for_indians'].apply(lambda x: ResponseCleanerService.fix_bool_flag(x))
        self.attributes_df['article_interest_duration'] = self.attributes_df['article_interest_duration'].apply(lambda x: ResponseCleanerService.fix_validity_duration(x))
        self.attributes_df['final_reader_interest_score'] = self.attributes_df['final_reader_interest_score'].apply(lambda x: ResponseCleanerService.fix_float(x))
        self.attributes_df['final_headline_effectiveness_score'] = self.attributes_df['final_headline_effectiveness_score'].apply(lambda x: ResponseCleanerService.fix_float(x))
        self.attributes_df['final_event_novelty_score'] = self.attributes_df['final_event_novelty_score'].apply(lambda x: ResponseCleanerService.fix_float(x))
        self.attributes_df['final_emotional_impact_score'] = self.attributes_df['final_emotional_impact_score'].apply(lambda x: ResponseCleanerService.fix_float(x))
        self.attributes_df['article_type'] = self.attributes_df['article_type'].apply(lambda x: ResponseCleanerService.fix_article_type(x))
        self.attributes_df['article_sentiment'] = self.attributes_df['article_sentiment'].apply(lambda x: ResponseCleanerService.fix_article_sentiment(x))
        self.attributes_df['is_summary_valid'] = self.attributes_df['improved_summary'].apply(lambda x: ResponseCleanerService.validate_summary(x))
        self.attributes_df['extracted_summary'] = self.attributes_df['improved_summary'].apply(lambda x: json.dumps(ResponseCleanerService.convert_summary_to_dicts(x)))
        self.attributes_df['is_emoji_valid'] = self.attributes_df['improved_summary'].apply(lambda x: ResponseCleanerService.validate_summary_emojis(x))
        float_cols = ['final_reader_interest_score', 'final_headline_effectiveness_score', 'final_event_novelty_score', 'final_emotional_impact_score']
        self.attributes_df[float_cols] = self.attributes_df[float_cols].fillna(value=0.33)
        self.attributes_df['cleaned_summary'] = self.attributes_df['improved_summary'].apply(lambda x: self.clean_text_emoji_summaries(x))
        self.attributes_df['cleaned_first_summary'] = self.attributes_df['summary'].apply(lambda x: self.clean_text_emoji_summaries(x))
        self.attributes_df['is_english'] = self.attributes_df['user_prompt'].apply(lambda x: self.is_english(x, threshold=0.9))
        self.attributes_df['is_valid_response'] = self.attributes_df.apply(lambda x: ResponseCleanerService.is_cleaned_response_valid(x), axis=1)

    @staticmethod
    def is_cleaned_response_valid(row):
        if not row['cleaned_summary'] or not row['cleaned_first_summary']:
            return False
        if not row['is_english']:
            return False
        has_null = any(pd.isnull(row[col]) for col in expected_keys if col in row.index)
        return not has_null

    @staticmethod
    def fix_category(cat):
        valid_cats = ['business', 'economic_policy', 'financial', 'irrelevant', 'personal_finance']
        cat = cat.lower()
        if cat in valid_cats:
            return cat
        if cat in ['finance']:
            return 'financial'
        else:
            return None

    @staticmethod
    def fix_india_flag(india_flag):
        valid_flags = ['indian', 'international']
        india_flag = india_flag.lower()
        if india_flag in valid_flags:
            return india_flag
        if india_flag == 'india':
            return 'indian'
        else:
            return None

    @staticmethod
    def is_english(text, threshold=0.9):
        # Count the number of characters that are in the ASCII range
        ascii_chars = sum(1 for char in text if ord(char) < 128)
        # Calculate the percentage of text that is ASCII
        ascii_percent = ascii_chars / len(text) if text else 0
        # Return True if the ASCII percentage is above the threshold
        return ascii_percent >= threshold

    @staticmethod
    def fix_bool_flag(bool_flag):
        trues = ['True', 'true', '1', 1, True]
        false = ['False', 'false', '0', 0, False]
        if bool_flag in trues:
            return True
        elif bool_flag in false:
            return False
        else:
            return None

    @staticmethod
    def fix_float(float_val):
        try:
            val = float(float_val)
            return val
        except:
            return None

    @staticmethod
    def convert_summary_to_dicts(input_str):
        # Regular expression to match each point
        point_pattern = re.compile(r'!(?P<emoji>.+?)! (?P<label>[^:!]+)(?:\: (?P<point>[^!]+))?')
        dicts = []

        for match in point_pattern.finditer(input_str):
            emoji = match.group('emoji').strip()
            label = match.group('label').strip()
            point_text = match.group('point').strip() if match.group('point') else ""

            # Validate emoji and ensure label and point are not empty
            if not any(ord(char) > 127 for char in emoji):
                return []
            if not label:
                return []
            if not point_text:
                return []

            dicts.append({'emoji': emoji, 'label': label, 'point': point_text})

        return dicts

    @staticmethod
    def validate_emoji(emoji):
        is_emoji = True
        for c in emoji:
            is_emoji = is_emoji and (ord(c) > 127)
        return is_emoji

    @staticmethod
    def validate_summary(summary):
        summary_dict = ResponseCleanerService.convert_summary_to_dicts(summary)
        if summary_dict:
            return True
        else:
            return False

    @staticmethod
    def validate_summary_emojis(summary):
        summary_dict = ResponseCleanerService.convert_summary_to_dicts(summary)
        if summary_dict:
            valid_emoji = True
            for point in summary_dict:
                valid_emoji = valid_emoji and ResponseCleanerService.validate_emoji(point['emoji'])
            return valid_emoji
        else:
            return False

    @staticmethod
    def convert_summary_dict_to_str_format(summary_dict):
        # Format each dictionary into the specified string pattern
        formatted_points = [
            f"!{item['emoji']}! {item['label']}: {item['point']}" for item in summary_dict
        ]
        # Join all formatted strings with "\n"
        return " \n ".join(formatted_points)

    def clean_text_emoji_summaries(self, summary):  # Convert a text emoji to emoji
        if ResponseCleanerService.validate_summary(summary):
            if ResponseCleanerService.validate_summary_emojis(summary):
                return summary
            else:
                summary_dict = ResponseCleanerService.convert_summary_to_dicts(summary)
                for point in summary_dict:
                    cur_emoji = point['emoji'].lower()
                    if len(cur_emoji.split(' ')) > 2:
                        return None
                    cur_emoji = cur_emoji.replace(' ', '_')
                    if cur_emoji not in EMOJIS:
                        self.missing_emoji_texts.append(cur_emoji)
                    point['emoji'] = EMOJIS.get(cur_emoji, "pushpin")
                return ResponseCleanerService.convert_summary_dict_to_str_format(summary_dict)
        else:
            return None

    @staticmethod
    def fix_article_type(article_type):
        article_type = article_type.lower()
        if article_type in ['fact', 'Fact', 'factual', 'announcement', 'news']:
            return 'fact'
        if article_type in ['research', 'forecast', 'investigation', 'analysis', 'review']:
            return 'analysis'
        if article_type in ['advice', 'opinion', 'interview', 'personal']:
            return 'opinion'
        if article_type in ['educational', 'education']:
            return 'educational'
        if article_type in ['sponsored', 'advertisement', 'promotion', 'ad']:
            return 'promotion'
        return None

    @staticmethod
    def fix_article_sentiment(sentiment):
        sentiment = sentiment.lower()
        if sentiment in ['bearish', 'bear']:
            return 'bear'
        if sentiment in ['bullish', 'bull']:
            return 'bull'
        if sentiment in ['na', 'neutral']:
            return 'na'
        return None

    @staticmethod
    def fix_validity_duration(val):  # If a value is 90 or 365 then set it as 30. less than -1 is -1
        val = int(val)
        valid_days = [-1, 1, 3, 7, 14, 30]
        if val in valid_days:
            return val
        else:
            valid_value = -1
            for i in valid_days:
                if val > i:
                    valid_value = i
            return valid_value
