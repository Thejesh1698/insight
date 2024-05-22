import psycopg2
from googleapiclient.discovery import build
import pandas as pd
import os
from google.oauth2.credentials import Credentials
from TokenManager import TokenManager
from sentence_transformers import SentenceTransformer
from PostgresDatabaseOperation import PostgresDatabaseOperation


sentence_transformer = SentenceTransformer(model_name_or_path='BAAI/bge-small-en-v1.5')

# def fetch_access_token_from_db(user_id):
#     with PostgresDatabaseOperation() as cursor:
#         sql = "SELECT access_token FROM slack_google_user_auth_tokens WHERE user_id = %s"
#         cursor.execute(sql, (user_id,))
#         result = cursor.fetchone()
#     if result:
#         return result[0]
#     else:
#         return None


def get_access_token_for_user(refresh_token, client_id, client_secret):
    access_token = TokenManager.refresh_access_token(refresh_token=refresh_token,
                                                     client_id=client_id,
                                                     client_secret=client_secret)
    return access_token


def list_all_google_docs(access_token):
    credentials = Credentials(access_token)
    drive_service = build('drive', 'v3', credentials=credentials)
    results = drive_service.files().list(
        fields="nextPageToken, files(id, name, mimeType)",
        pageSize=100,
        # spaces='drive',
        q="mimeType='application/vnd.google-apps.document'"
    ).execute()
    return results['files']


def get_google_doc_content_by_id(doc_id, access_token):
    credentials = Credentials(access_token)
    drive_service = build('drive', 'v3', credentials=credentials)
    doc_content = drive_service.files().export(fileId=doc_id, mimeType='text/plain').execute()
    return doc_content


def get_all_docs_and_embeddings(access_token):
    all_files = list_all_google_docs(access_token=access_token)
    docs_data = {}
    for file in all_files:
        doc_id = file['id']
        docs_data[doc_id] = {}
        docs_data[doc_id]['name'] = file['name']
        content = get_google_doc_content_by_id(doc_id=doc_id, access_token=access_token)
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        embedding = create_embeddings_for_document(doc_content=content)
        docs_data[doc_id]['embeddings'] = embedding
        docs_data[doc_id]['content'] = content
    return docs_data
# def save_docs_to_database(file_contents, embeddings)


def write_doc_data_db(docs_data, user_id):
    with PostgresDatabaseOperation() as cursor:
        sql = """
        INSERT INTO google_docs_texts (user_id, doc_id, doc_name, doc_content, embedding)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, doc_id)
        DO UPDATE SET
        doc_name = EXCLUDED.doc_name,
        doc_content = EXCLUDED.doc_content,
        embedding = EXCLUDED.embedding,
        updated_at = CURRENT_TIMESTAMP
        """
        for doc_id, cur_doc_data in docs_data.items():
            doc_name = cur_doc_data.get('name')
            doc_content = cur_doc_data.get('content')
            embedding = cur_doc_data.get('embeddings')
            if doc_name and doc_content and embedding:
                cursor.execute(sql, (user_id, doc_id, doc_name, doc_content, embedding))

#
# def insert_or_update_google_doc_text(user_id, doc_id, doc_name, doc_content):
#     current_time = datetime.datetime.now()
#
#     with psycopg2.connect(**db_credentials) as conn:
#         with conn.cursor() as cursor:
#             # Check if the record exists for the combination of user_id and doc_id
#             cursor.execute(
#                 "SELECT id FROM google_docs_texts WHERE user_id = %s AND doc_id = %s",
#                 (user_id, doc_id),
#             )
#             doc_exists = cursor.fetchone()
#
#             if doc_exists:
#                 # Update existing record
#                 cursor.execute(
#                     "UPDATE google_docs_texts SET doc_name = %s, doc_content = %s, updated_at = %s WHERE user_id = %s AND doc_id = %s",
#                     (doc_name, doc_content, current_time, user_id, doc_id),
#                 )
#             else:
#                 # Insert new record
#                 cursor.execute(
#                     "INSERT INTO google_docs_texts (user_id, doc_id, doc_name, doc_content, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
#                     (user_id, doc_id, doc_name, doc_content, current_time, current_time),
#                 )
#
def create_embeddings_for_document(doc_content):
    # if isinstance(doc_content, bytes):
    #     doc_content = doc_content.decode('utf-8')
    embeddings = sentence_transformer.encode(doc_content, convert_to_numpy=True)
    embeddings = list(embeddings)
    embeddings = [float(x) for x in embeddings]
    # TODO: - add validation here
    return embeddings


def fetch_google_docs(access_token):
    drive_service = build('drive', 'v3', credentials=access_token)
    results = drive_service.files().list(
        fields="nextPageToken, files(id, name, mimeType)",
        pageSize=100,
        spaces='drive',
        q="mimeType='application/vnd.google-apps.document'"
    ).execute()
    items = results.get('files', [])
    return items  # List of Google Docs (id, name, mimeType)
