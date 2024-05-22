import json
import logging
import boto3
from bertopic.backend._sentencetransformers import SentenceTransformerBackend
from sentence_transformers import SentenceTransformer
from sql.embeddings.EmbeddingSQL import EmbeddingSQL
from typing import List, Dict

from src.data_models.Article import Article
logger = logging.getLogger(__name__)


class EmbeddingsService:

    def __init__(self, hf_model_path: str):
        self.model_name = hf_model_path
        self.sentence_transformer = SentenceTransformer(model_name_or_path=self.model_name)
        # self.sentence_transformer = embedding_model

        # self.sagemaker_runtime = boto3.client("sagemaker-runtime", region_name='ap-south-1')
        # TODO: - move to conf or env variable
        # self.endpoint = 'huggingface-pytorch-inference-2023-10-30-13-16-43-720'

    def create_article_embeddings(self, article: Article):
        # TODO: - get this data from mongo
        if article.full_content:
            logger.info(f'embeddings triggered for {article.article_id}')
            embeddings = self.extract_embeddings_for_text(content=article.full_content)
            logger.info(f'embeddings extracted for {article.article_id}')
            # TODO: - the model name should come from sagemaker
            # TODO: - use article content_type
            EmbeddingSQL.upsert_embeddings(article_id=article.article_id, embeddings=embeddings, model_name='BAAI/bge-large-en-v1.5', content_type=article.content_type)
            logger.info(f'embeddings saved for {article.article_id}')
        else:
            print(f"Not a valid article content. Embeddings are not generated for {article.article_id}")

    def extract_embeddings_for_text(self, content: str) -> List[float]:
        # embeddings = self.sentence_transformer.embed(content)
        embeddings = self.sentence_transformer.encode(content, convert_to_numpy=True)
        embeddings = list(embeddings)
        embeddings = [float(x) for x in embeddings]
        # TODO: - add validation here
        return embeddings

        # input_dct = {"inputs": f"{content}"}
        # response = self.sagemaker_runtime.invoke_endpoint(
        #     EndpointName=self.endpoint,
        #     Body=bytes(f'{input_dct}'.replace("'", '"'), 'utf-8'),
        #     ContentType='application/json'
        # )
        # vec = response['Body']
        # vec = json.loads(vec.read())
        # embeddings = vec['vectors'][0]
        # # TODO: - add validation here
        # return embeddings
