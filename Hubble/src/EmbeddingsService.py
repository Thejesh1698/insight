import json
import logging
from sentence_transformers import SentenceTransformer
import requests
from src.constants import embeddings_endpoint
import boto3
from sql.SearchSQL import SearchSQL
from typing import List, Dict

sagemaker_runtime = boto3.client("sagemaker-runtime", region_name='ap-south-1')


class EmbeddingsService:

    def __init__(self, hf_model_path: str):
        self.model_name = hf_model_path
        self.sentence_transformer = SentenceTransformer(model_name_or_path=self.model_name)

    def extract_embeddings_for_text(self, content: str) -> List[float]:
        embeddings = self.sentence_transformer.encode(content, convert_to_numpy=True)
        embeddings = list(embeddings)
        embeddings = [float(x) for x in embeddings]
        # TODO: - add validation here
        return embeddings

    @staticmethod
    def get_search_query_embeddings(content: str) -> List[float]:
        # input_dct = {"inputs": f"{content}"}
        # response = sagemaker_runtime.invoke_endpoint(
        #     EndpointName=embeddings_endpoint,
        #     Body=bytes(f'{input_dct}'.replace("'", '"'), 'utf-8'),
        #     ContentType='application/json'
        # )
        # vec = response['Body']
        # vec = json.loads(vec.read())
        # embeddings = vec['vectors'][0]
        logging.info('embeddings server called')
        url = 'http://Arcane-env.eba-mrsaixmg.ap-south-1.elasticbeanstalk.com/create_embedding_for_text'
        r = requests.post(url, json={'query_text': content})
        embeddings = json.loads(r.text)
        logging.info('embeddings received')
        # TODO: - add validation here
        return embeddings
