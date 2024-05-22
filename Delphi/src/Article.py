import logging
from dataclasses import dataclass, asdict
import re
from typing import Union


@dataclass
class Article:
    article_id: str
    title: str
    cleaned_text: str
    is_premium_article: bool
    published_time: str
    source_id: str
    source_name: str
    url: str
    full_content: str = None

    @classmethod
    def from_dict(cls, data: dict):
        key_mapping = {
            'articleId': 'article_id',
            'title': 'title',
            'cleaned_text': 'cleaned_text',
            'isPremiumArticle': 'is_premium_article',
            'publishedTime': 'published_time',
            'sourceId': 'source_id',
            'sourceName': 'source_name',
            'url': 'url'
        }

        processed_data = {key_mapping[k]: v for k, v in data.items() if k in key_mapping}

        if 'title' in processed_data and 'cleaned_text' in processed_data:
            full_content = cls.__generate_full_content(processed_data['title'], processed_data['cleaned_text'])
            full_content = cls.__clean_article_content(article_content=full_content)
            if not cls.__is_article_content_valid(article_content=full_content, article_id=processed_data['article_id']):
                full_content = None
            processed_data['full_content'] = full_content

        return cls(**processed_data)

    def to_dict(self) -> dict:
        # Mapping the dataclass fields to the desired dictionary key names.
        key_mapping = {
            'article_id': 'articleId',
            'title': 'title',
            'cleaned_text': 'cleaned_text',
            'is_premium_article': 'isPremiumArticle',
            'published_time': 'publishedTime',
            'source_id': 'sourceId',
            'source_name': 'sourceName',
            'full_content': 'full_content',
            'url': 'url'
        }
        original_dict = asdict(self)
        return {key_mapping[key]: value for key, value in original_dict.items()}

    @staticmethod
    def __generate_full_content(title: str, cleaned_text: str) -> str:
        return title + ': ' + cleaned_text

    @staticmethod
    def __clean_article_content(article_content: str) -> Union[str, None]:
        # removing new line symbol
        article_content = article_content.replace('\n', '')
        article_content = article_content.replace('\t', '')
        # removing characters which are not part of alphabets, numbers, currencies, percent, dot, dash, brackets, space, slash
        article_content = re.sub(r"[^a-zA-Z0-9$€₹%\-:/()\[\]{} .]", "", article_content)
        return article_content

    @staticmethod
    def __is_article_content_valid(article_content: str, article_id: str) -> Union[bool, None]:
        # ensure that there are at least 10 words and 30 characters
        if len(article_content.split(" ")) >= 10 and len(article_content) >= 30:
            return True
        else:
            logging.warning(f"cleaned article {article_id} - {article_content} has less than 10 words or 30 characters")
            return False
