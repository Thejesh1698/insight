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
from src.Article import Article

logger = logging.getLogger(__name__)


# if not os.getenv('AWS_ACCESS_KEY') or not os.getenv('AWS_SECRET_KEY'):
#     raise EnvironmentError("Missing AWS credentials")

class ArticleService:

    @staticmethod
    def get_Article(article_id: str) -> Union[Article, None]:
        article_json = ArticleService.__get_article_json_from_s3_and_api(article_id=article_id)
        is_valid = ArticleService.__validate_article_json(article_json=article_json, article_id=article_id)
        if is_valid:
            article = ArticleService.__load_json_as_Article(article_json=article_json, article_id=article_id)
            return article
        else:
            return None

    @staticmethod
    def parallel_get_Articles(article_ids: List[str]) -> dict[str, Article]:
        """
        Parallel download of titles, returning a dictionary of article_ids and their corresponding Articles.
        """
        article_data = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            # Start the load operations and mark each future with its article ID
            future_to_article_id = {executor.submit(ArticleService.get_Article, article_id): article_id for article_id in article_ids}

            for future in as_completed(future_to_article_id):
                article_id = future_to_article_id[future]
                try:
                    article_id_data = future.result()
                    if article_id_data:
                        article_data[article_id] = article_id_data
                except Exception as e:
                    print(f"Error downloading title for article ID {article_id}: {e}")
        return article_data

    @staticmethod
    def __get_article_json_from_s3_and_api(article_id: str) -> dict:
        article_json = ArticleService.__get_article_text_from_s3(article_id=article_id)
        article_metadata_json = ArticleService.__get_article_metadata_from_api(article_id=article_id)
        article_json.update(article_metadata_json)
        assert 'source' in article_metadata_json, f"source not present in the metadata json"
        article_json.update(article_metadata_json['source'])
        return article_json

    @staticmethod
    def __get_article_metadata_from_api(article_id: str) -> Union[dict, None]:
        print(f'article_id is {article_id}')
        # TODO: - move to a conf
        try:
            url = f"http://insight-user-app-beta-env.eba-rnrpvmin.ap-south-1.elasticbeanstalk.com/articles/{article_id}?fetchSourceInfo=true"
            response = requests.get(url)
            meta_data = json.loads(response.text)
            return meta_data
        except HTTPError as e:
            logger.error(f"error getting article metadata for article id {article_id}: {e}")
        except JSONDecodeError as e:
            logger.error(f"error loading the json from metadata text for article id {article_id}: {e}")
        except Exception as e:
            logger.error(f'error getting data from api {e}')
        return None

    @staticmethod
    def __get_article_text_from_s3(article_id: str) -> Union[json, None]:
        # TODO: - should we centralize the env variables?
        bucket_name = 'insight-articles-content'
        object_key = f"{article_id}/cleaned_data.json"

        try:
            session = boto3.session.Session()
            s3 = session.client('s3', aws_access_key_id=os.environ.get("AWS_ACCESS_KEY"), aws_secret_access_key=os.environ.get("AWS_SECRET_KEY"))
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
            print(f'error getting data from api {e}')
            logger.error(f"An unexpected error occurred: {e}")
        return None

    @staticmethod
    def __validate_article_json(article_json, article_id) -> Union[bool, None]:
        for key in ['cleaned_text', 'isPremiumArticle', 'title', 'articleId', 'publishedTime', 'sourceId', 'url']:
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
            logging.error(f"unable to cast article json of {article_id} to Article datatype - likely is missing cleaned_text or meta_data")
            return None
