import logging
from dataclasses import dataclass, asdict
import re
from typing import Union
from src.constants import SourceType, ContentType


@dataclass
class Article:
    article_id: str
    title: str
    is_premium_article: bool
    source_id: str
    url: str
    cleaned_text: str = ''
    content_type: str = ContentType.article.value
    short_description: str = ''
    published_time: str = None
    image_url: str = None
    full_content: str = None

    @classmethod
    def from_dict(cls, data: dict, only_metadata: bool = False):
        expected_keys = ['article_id', 'title', 'cleaned_text', 'is_premium_article', 'published_time', 'source_id', 'image_url', 'url', 'content_type', 'short_description']
        processed_data = {k: v for k, v in data.items() if k in expected_keys}

        if 'content_type' in data and data['content_type'] == ContentType.podcast_episode.value:
            if 'short_description' in processed_data:
                full_content = cls.__generate_full_content(processed_data['title'], processed_data['short_description'])
            else:
                full_content = cls.__generate_full_content(processed_data['title'], '')
            full_content = cls.__clean_article_content(article_content=full_content)
            if not cls.__is_article_content_valid(article_content=full_content, article_id=processed_data['article_id']):
                full_content = None
            processed_data['full_content'] = full_content
        elif only_metadata or 'cleaned_text' not in processed_data:   # don't do validation on only title. # TODO: - do an analysis on distribution and check if checks are needed
            full_content = cls.__clean_article_content(article_content=processed_data['title'])
            processed_data['full_content'] = full_content
        elif 'title' in processed_data and 'cleaned_text' in processed_data:
            full_content = cls.__generate_full_content(processed_data['title'], processed_data['cleaned_text'])
            full_content = cls.__clean_article_content(article_content=full_content)
            if not cls.__is_article_content_valid(article_content=full_content, article_id=processed_data['article_id']):
                full_content = None
            processed_data['full_content'] = full_content
        return cls(**processed_data)

    def to_dict(self) -> dict:
        # Mapping the dataclass fields to the desired dictionary key names.
        return asdict(self)
        # return original_dict

    @staticmethod
    def __generate_full_content(title: str, cleaned_text: str) -> str:
        return f'headline: {title}. \n content: {cleaned_text}'

    @staticmethod
    def __clean_article_content(article_content: str) -> Union[str, None]:
        # removing new line symbol
        article_content = article_content.replace('\n', '')
        article_content = article_content.replace('\t', '')
        # removing characters which are not part of alphabets, numbers, currencies, percent, dot, dash, brackets, space, slash
        # article_content = re.sub(r"[^a-zA-Z0-9$€₹%\-:/()\[\]{} <>?,.]", "", article_content)
        return article_content

    @staticmethod
    def __is_article_content_valid(article_content: str, article_id: str) -> Union[bool, None]:
        # ensure that there are at least 10 words and 30 characters
        if len(article_content.split(" ")) >= 10 and len(article_content) >= 30:
            return True
        else:
            logging.warning(f"cleaned article {article_id} - {article_content} has less than 10 words or 30 characters")
            return False
