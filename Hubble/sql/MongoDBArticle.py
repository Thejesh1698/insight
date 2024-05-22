import os
from datetime import datetime, timezone, timedelta
from src.constants import INDIAN_SOURCES
import pandas as pd
from bson import ObjectId
from sql.MongoDatabaseConnection import MongoDatabaseConnection


class MongoDBArticle:

    @staticmethod
    def get_db():
        mongo_conn = None
        try:
            # setup mongo connection
            mongo_conn = MongoDatabaseConnection()
            mongo_client = mongo_conn.get_client()
            db = mongo_client[os.environ.get("MONGO_DB_NAME")]
            return db
        except Exception as e:
            if mongo_conn:
                mongo_conn.close_connection()
            raise Exception(f"Error in connecting to db: {e}")

    @staticmethod
    def get_collection(collection_name=None):
        try:
            db = MongoDBArticle.get_db()
            if collection_name is None:
                return db[os.environ.get("MONGO_COLLECTION_NAME")]
            else:
                return db[collection_name]
        except Exception as e:
            raise Exception(f"Error in _get_collection: {e}")

    @staticmethod
    def fetch_documents_by_ids(string_ids, max_published_date=None, indian_sources_only=False):
        try:
            object_ids = [ObjectId(string_id) for string_id in string_ids]
        except Exception as e:
            return f"Invalid ID format: {e}"

        collection = MongoDBArticle.get_collection()
        query = {"_id": {"$in": object_ids}}

        if max_published_date:
            query["published_time"] = {"$lt": max_published_date}
        if indian_sources_only:
            indian_source_object_ids = [ObjectId(string_id) for string_id in INDIAN_SOURCES]
            query["source_id"] = {"$in": indian_source_object_ids}
        documents = list(collection.find(query))
        doc_dict = {}
        for doc in documents:
            article_id = str(doc.pop('_id'))
            doc_dict[article_id] = doc
            doc_dict[article_id]['article_id'] = article_id
            doc_dict[article_id]['source_id'] = str(doc['source_id'])
            doc_dict[article_id]['is_premium_article'] = False
        return doc_dict

    @staticmethod
    def fetch_article_published_time_df(article_ids):
        article_object_ids = [ObjectId(a_id) for a_id in article_ids]

        query = {
            "is_premium_article": False, "_id": {"$in": article_object_ids}
        }
        projection = {
            "_id": 1, "published_time": 1
        }

        collection = MongoDBArticle.get_collection()
        documents = list(collection.find(query, projection))
        df = pd.DataFrame(
            [{'article_id': str(doc['_id']), 'published_time': doc['published_time']} for doc in documents]
        )
        return df

    @staticmethod
    def fetch_all_document_ids():
        query = {"is_premium_article": False}
        projection = {"_id": 1}

        collection = MongoDBArticle.get_collection()
        documents = list(collection.find(query, projection))
        return [str(doc['_id']) for doc in documents]

    @staticmethod
    def fetch_recent_published_document_ids(days):
        collection = MongoDBArticle.get_collection()

        today = datetime.now(timezone.utc)
        start_date = today - timedelta(days=days)

        query = {
            "is_premium_article": False,
            "published_time": {"$gte": start_date.isoformat()}
        }
        projection = {
            "_id": 1
        }
        documents = list(collection.find(query, projection))
        return [str(doc['_id']) for doc in documents]

    @staticmethod
    def fetch_metadata_for_all_articles():
        query = {
            "is_premium_article": False
        }

        # Projection to specify which fields to include
        projection = {
            "_id": 1, "published_time": 1, "source_id": 1, "url": 1, "title": 1, "image_url": 1, "content_type": 1
        }

        collection = MongoDBArticle.get_collection()
        documents = list(collection.find(query, projection))
        doc_dict = {}
        for doc in documents:
            article_id = str(doc.pop('_id'))
            doc_dict[article_id] = doc
            doc_dict[article_id]['article_id'] = article_id
            doc_dict[article_id]['source_id'] = str(doc['source_id'])
            doc_dict[article_id]['is_premium_article'] = False
        return doc_dict

    @staticmethod
    def fetch_metadata_for_article_ids(article_ids):

        article_object_ids = [ObjectId(a_id) for a_id in article_ids]

        # Query to find documents where 'is_premium_article' is False and '_id' is in article_ids
        query = {
            "is_premium_article": False,
            "_id": {"$in": article_object_ids}
        }

        # Projection to specify which fields to include
        projection = {"_id": 1, "published_time": 1, "source_id": 1, "url": 1, "title": 1, "image_url": 1, 'short_description': 1, 'content_type': 1}

        collection = MongoDBArticle.get_collection()
        documents = list(collection.find(query, projection))
        doc_dict = {}
        for doc in documents:
            article_id = str(doc.pop('_id'))
            doc_dict[article_id] = doc
            doc_dict[article_id]['article_id'] = article_id
            doc_dict[article_id]['source_id'] = str(doc['source_id'])
            doc_dict[article_id]['is_premium_article'] = False
        return doc_dict

    @staticmethod
    def convert_to_json_serializable(documents):
        for doc in documents:
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
        return documents

    @staticmethod
    # TODO: - this shouldn't be part of articles
    def save_llm_response_to_collection(document):
        collection_name = 'llm_responses'
        collection = MongoDBArticle.get_collection(collection_name=collection_name)
        return collection.insert_one(document).inserted_id
