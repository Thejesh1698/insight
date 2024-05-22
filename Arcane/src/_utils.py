import json
import os
import pickle
import psutil
import tempfile
from copy import deepcopy
from io import BytesIO, StringIO
import sys
import boto3
import joblib
import pandas as pd
from bertopic import BERTopic
from bertopic.backend._sentencetransformers import SentenceTransformerBackend

from sql.clustering.ClusteringSQL import ClusteringSQL
from smart_open import open
# TODO: - move credentials to conf/env variable
# TODO: - move this to a class perhaps?
s3_bucket = 'insight-ml-models'
s3_bertopic_folder = 'bertopic'


def load_bertopic_model_from_hf(run_id=None) -> BERTopic:
    """
    Function infers the bertopic model based on latest run id.
    Embedding model is loaded using the config used in the run
    :return: loaded bertopic model
    """
    # model path not declared in environment variables
    # if os.environ.get('BERTOPIC_MODEL') is not None:
    #     model_path = os.environ.get('BERTOPIC_MODEL')
    #     embedding_model_name = os.environ.get('EMBEDDING_MODEL')
    #     assert embedding_model_name is not None, f"BERTOPIC_MODEL provided in env but not EMBEDDING_MODEL"
    # else:
    if run_id is None:
        run_id = ClusteringSQL.get_latest_run_id()
    assert run_id is not None, f"no latest clustering run id found, unable to find model to load"
    # TODO: - is_dev to be moved to env variables
    model_path = generate_hf_model_name(run_id=run_id, is_dev=False)

    embedding_model_name = get_embedding_model_name(run_id=run_id)
    bertopic_model = BERTopic.load(path=model_path, embedding_model=embedding_model_name)
    return bertopic_model


def save_bertopic_model_to_hf(model: BERTopic, run_id: str, is_dev: bool):
    repo_id = generate_hf_model_name(run_id=run_id, is_dev=is_dev)
    model.push_to_hf_hub(repo_id=repo_id,
                         token=os.environ.get('HF_TOKEN'),
                         private=True,
                         model_card=True,
                         serialization='safetensors',
                         save_embedding_model=True,
                         save_ctfidf=True)


def save_file_to_s3_model_folder(run_id, data, filename, filetype):
    folder_name = run_id
    s3_resource = boto3.resource('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
    if filetype == '.csv':
        assert isinstance(data, pd.DataFrame), f"data for filename {filename} is not of type dataframe to save as csv"
        csv_buffer = StringIO()
        data.to_csv(csv_buffer)
        filename = filename + '.csv'
        s3_resource.Object(s3_bucket, f'{s3_bertopic_folder}/{folder_name}/{filename}').put(Body=csv_buffer.getvalue())
    elif filetype == '.json':
        assert isinstance(data, dict), f"data for filename {filename} is not of type dict to save as json"
        filename = filename + '.json'
        s3_resource.Object(s3_bucket, f'{s3_bertopic_folder}/{folder_name}/{filename}').put(Body=json.dumps(data))


def save_bertopic_model_to_s3(model: BERTopic, run_id: str):
    folder_name = run_id
    filename = 'BERTopic_' + run_id
    model = deepcopy(model)
    model.embedding_model = None
    s3_resource = boto3.resource('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
    pickle_byte_obj = pickle.dumps(model)
    s3_resource.Object(s3_bucket, f'{s3_bertopic_folder}/{folder_name}/{filename}').put(Body=pickle_byte_obj)


# def save_bertopic_model_to_s3(model: BERTopic, run_id: str):
#     filename = 'BERTopic_' + run_id
#     model = deepcopy(model)
#     model.embedding_model = None
#     s3_resource = boto3.resource('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
#     # pickle_byte_obj = pickle.dumps(model)
#     with tempfile.TemporaryFile() as fp:
#         joblib.dump(model, fp)
#         fp.seek(0)
#         s3_resource.Object(s3_bucket, f'{s3_bertopic_folder}/{filename}').put(Body=fp.read())


def load_bertopic_model_from_s3(run_id: str, hf_embedding_model_name: str) -> BERTopic:
    filename = 'BERTopic_' + run_id
    foldername = run_id
    s3_path = f's3://{s3_bucket}/{s3_bertopic_folder}/{foldername}/{filename}'
    print(f'RAM left before streaming BERTOPIC is {psutil.virtual_memory().available / (1024.0 * 1024.0)}')
    # Stream the model directly from S3
    with open(s3_path, 'rb',
              transport_params={'client': boto3.client('s3',
                                                       aws_access_key_id=os.environ['AWS_ACCESS_KEY'],
                                                       aws_secret_access_key=os.environ['AWS_SECRET_KEY'])}) as f:
        model = pickle.load(f)
    print('bertopic streamed successfully')
    print(f'RAM left after streaming BERTopic is {psutil.virtual_memory().available / (1024.0 * 1024.0)}')
    print(f'clustering model is of size {sys.getsizeof(model)/(1024 * 1024)} mb')
    print(f'model is instance of bertopic as {isinstance(model, BERTopic)}')

    assert isinstance(model, BERTopic), f"Failed to load model from S3. Model {filename} is not of type BERTopic."
    emb_model = SentenceTransformerBackend(embedding_model=hf_embedding_model_name)
    print(f'embedding model loaded for bertopic with size of {sys.getsizeof(emb_model)/(1024 * 1024)} mb')
    model.embedding_model = emb_model
    print('embedding model loaded onto bertopic')
    return model
#
# def load_bertopic_model_from_s3(run_id: str, hf_embedding_model_name: str) -> BERTopic:
#     filename = 'BERTopic_' + run_id
#     s3_resource = boto3.resource('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
#     response = s3_resource.Object(s3_bucket, f'{s3_bertopic_folder}/{filename}').get()
#     print('fetched the s3 file')
#     body_string = response['Body'].read()
#     print('the body string has been read')
#     model = pickle.loads(body_string)
#     print('the model has been loaded now')
#     assert isinstance(model, BERTopic), f"Filed to load model from S3. model {filename} is not of type BERTopic. "
#     model.embedding_model = SentenceTransformerBackend(embedding_model=hf_embedding_model_name)
#     return model


# def load_bertopic_model_from_s3(run_id: str, hf_embedding_model_name: str) -> BERTopic:
#     filename = 'BERTopic_' + run_id
#     s3_resource = boto3.resource('s3', aws_access_key_id=os.environ['AWS_ACCESS_KEY'], aws_secret_access_key=os.environ['AWS_SECRET_KEY'])
#     with BytesIO() as data:
#         s3_resource.Bucket(s3_bucket).download_fileobj(f'{s3_bertopic_folder}/{filename}', data)
#         data.seek(0)    # move back to the beginning after writing
#         model = joblib.load(data)
#     assert isinstance(model, BERTopic), f"Filed to load model from S3. model {filename} is not of type BERTopic. "
#     model.embedding_model = SentenceTransformerBackend(embedding_model=hf_embedding_model_name)
#     return model


def generate_hf_model_name(run_id: str, is_dev: bool) -> str:
    model_name = 'BERTopic_' + run_id
    if is_dev:
        model_name += '_dev'
    repo_id = f'WintWealth/{model_name}'
    return repo_id


def get_embedding_model_name(run_id) -> str:
    latest_run_config = ClusteringSQL.get_config_for_run_id(run_id=run_id)
    embedding_model_name = latest_run_config['embedding_model_name']
    return embedding_model_name


def get_embedding_model_size(run_id) -> int:
    latest_run_config = ClusteringSQL.get_config_for_run_id(run_id=run_id)
    embedding_size = latest_run_config['embedding_size']
    return embedding_size


def load_topic_to_cluster_map(topic_to_cluster_json_path):
    with open(topic_to_cluster_json_path) as f:
        topic_to_cluster_map = json.load(f)
    return topic_to_cluster_map
