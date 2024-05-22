import os
import json
import boto3
import logging
import requests
from typing import Union, List
from requests import HTTPError
from json import JSONDecodeError
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import NoCredentialsError, ClientError
from sql.MongoDBArticle import MongoDBArticle
from src.constants import ContentType
from src.Article import Article
from sql.MongoDatabaseConnection import MongoDatabaseConnection

logger = logging.getLogger(__name__)


# if not os.getenv('AWS_ACCESS_KEY') or not os.getenv('AWS_SECRET_KEY'):
#     raise EnvironmentError("Missing AWS credentials")

class ArticleService:

    @staticmethod
    def get_Article(article_id: str) -> Union[Article, None]:
        article_json = ArticleService.__get_article_json_from_s3_and_mongo(article_id=article_id)
        is_valid = ArticleService.__validate_article_json(article_json=article_json, article_id=article_id)
        if is_valid:
            article = ArticleService.__load_json_as_Article(article_json=article_json, article_id=article_id)
            return article
        else:
            return None

    # @staticmethod
    # def get_Article_using_api(article_id: str) -> Union[Article, None]:
    #     article_json = ArticleService.get_article_json_from_s3_and_api(article_id=article_id)
    #     is_valid = ArticleService.__validate_article_json(article_json=article_json, article_id=article_id)
    #     if is_valid:
    #         article = ArticleService.__load_json_as_Article(article_json=article_json, article_id=article_id)
    #         return article
    #     else:
    #         return None
    #
    # @staticmethod
    # def get_article_json_from_s3_and_api(article_id: str) -> dict:
    #     article_json = ArticleService.get_article_text_from_s3(article_id=article_id)
    #     article_metadata_json = ArticleService._get_article_metadata_from_api(article_id=article_id)
    #     # return article_metadata_json
    #     # article_metadata_full_json = MongoDatabaseConnection.fetch_metadata_for_article_ids(article_ids=[article_id])
    #     # cur_article_metadata_json = article_metadata_full_json[article_id]
    #     metadata_keys = ['is_premium_article', 'title', 'article_id', 'published_time', 'source_id', 'url']
    #     # for key in metadata_keys:
    #     #     article_json[key] = cur_article_metadata_json[key]
    #     article_json.update(article_metadata_json)
    #     assert 'source' in article_metadata_json, f"source not present in the metadata json"
    #     article_json.update(article_metadata_json['source'])
    #     return article_json

    @staticmethod
    def get_article_content_from_s3(article_id: str) -> str:
        # TODO: - should we centralize the env variables?
        bucket_name = 'insight-articles-content'
        object_key = f"{article_id}/cleaned_data.json"

        try:
            session = boto3.session.Session()
            s3 = session.client('s3', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"), aws_secret_access_key=os.environ.get("AWS_SECRET_KEY"))
            s3_object = s3.get_object(Bucket=bucket_name, Key=object_key)
            article_json = json.loads(s3_object['Body'].read())
            if 'cleaned_text' in article_json:
                return f'title: {article_json["meta_data"]["title"]}. published_date: {article_json["meta_data"]["published_time"]}. content: {article_json["cleaned_text"]}'
            else:
                return f'title: {article_json["meta_data"]["title"]}'

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == "NoSuchKey":
                # Handle a missing object in the bucket
                logger.error("No such object in the bucket.")
            elif error_code == "InvalidAccessKeyId":
                # Handle an invalid access key ID
                logger.error("Invalid access key ID.")

        except NoCredentialsError:
            logger.error("No credentials available to complete the AWS request.")

        except Exception as e:
            # Optional: catch-all for other exceptions.
            logger.error(f"An unexpected error occurred: {e}")
        return None

    @staticmethod
    def get_Articles_from_list(article_id_list, max_published_date=None, indian_sources_only=False) -> [Article]:
        article_documents = MongoDBArticle.fetch_documents_by_ids(article_id_list, max_published_date=max_published_date, indian_sources_only=indian_sources_only)
        articles = {}
        for article_id in article_documents.keys():
            articles[article_id] = Article.from_dict(article_documents[article_id])
        return articles

    @staticmethod
    def get_all_Articles_metadata() -> dict[str: Article]:
        # TODO: - getting metadata of only articles with image_url
        all_article_metadata = MongoDBArticle.fetch_metadata_for_all_articles()

        metadata_dict = {}
        for article_id in all_article_metadata.keys():
            cur_article = Article.from_dict(all_article_metadata[article_id], only_metadata=True)
            # ignore if articles don't have images
            if cur_article.content_type == ContentType.article.value and cur_article.image_url is None:
                continue
            else:
                metadata_dict[article_id] = cur_article
        return metadata_dict

    @staticmethod
    def __get_article_json_from_s3_and_mongo(article_id: str) -> dict:
        article_json = ArticleService.get_article_text_from_s3(article_id=article_id)
        article_metadata_full_json = MongoDBArticle.fetch_metadata_for_article_ids(article_ids=[article_id])
        cur_article_metadata_json = article_metadata_full_json[article_id]
        if article_json:
            article_json.update(cur_article_metadata_json)
        else:
            article_json = cur_article_metadata_json
        return article_json

    @staticmethod
    def get_article_text_from_s3(article_id: str) -> Union[dict, None]:
        # TODO: - should we centralize the env variables?
        bucket_name = 'insight-articles-content'
        object_key = f"{article_id}/cleaned_data.json"

        try:
            session = boto3.session.Session()
            s3 = session.client('s3', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"),
                                aws_secret_access_key=os.environ.get("AWS_SECRET_KEY"))
            s3_object = s3.get_object(Bucket=bucket_name, Key=object_key)
            article_json = json.loads(s3_object['Body'].read())
            return article_json

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == "NoSuchKey":
                # Handle a missing object in the bucket
                logger.error("No such object in the bucket.")
            elif error_code == "InvalidAccessKeyId":
                # Handle an invalid access key ID
                logger.error("Invalid access key ID.")

        except NoCredentialsError:
            logger.error("No credentials available to complete the AWS request.")

        except Exception as e:
            # Optional: catch-all for other exceptions.
            logger.error(f"An unexpected error occurred: {e}")
        return None

    @staticmethod
    def __validate_article_json(article_json, article_id) -> Union[bool, None]:
        expected_keys = ['is_premium_article', 'title', 'article_id',
                         'published_time', 'source_id', 'url']
        for key in expected_keys:
            try:
                assert key in article_json
            except AssertionError as e:
                logging.error(f"{key} not present for article {article_id}: {e}")
                return False
        return True

    @staticmethod
    def __load_json_as_Article(article_json: dict, article_id: str) -> Union[Article, None]:
        try:
            article_obj = Article.from_dict(article_json)
            return article_obj
        except Exception:
            logging.error(
                f"unable to cast article json of {article_id} to Article datatype - likely is missing cleaned_text or meta_data")
            return None
