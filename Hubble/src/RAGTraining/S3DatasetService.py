import os
from datetime import datetime
from transformers import AutoTokenizer
from src.RAGTraining._utils.pack_dataset import pack_dataset
from datasets import Dataset
import pandas as pd
import re
import json
import numpy as np
import sagemaker
import boto3


class S3DatasetService:

    def __init__(self, hf_model_id, cleaned_responses_path, is_yi_model=False):
        self.model_id = hf_model_id
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        self.responses_path = cleaned_responses_path
        self.responses_df = pd.read_csv(self.responses_path)
        self.responses_df = self.responses_df.sample(frac=1)
        self.SYSTEM_PROMPT = list(self.responses_df['system_prompt'].unique())[0]
        self.message_template = [{"role": "system", "content": self.SYSTEM_PROMPT},
                                 {"role": "user", "content": ''}]
        self.system_tokens = len(self.tokenizer.apply_chat_template(self.message_template, add_generation_prompt=True))
        self.output_tokens = 768
        self.total_tokens = 6144
        self.buffer_tokens = 20
        self.lm_dataset = None
        self.finetune_id = ''
        self.finetune_dataset_config = {}
        self.sess = None
        self.is_yi_model = is_yi_model

        if is_yi_model:
            self.tokenizer.bos_token = '<s>'
            self.tokenizer.eos_token = '</s>'

    def create_dataset_and_upload(self):
        self._initiate_sagemaker_session()
        self._create_dataset()
        self._generate_finetune_config()
        self._upload_dataset_to_s3()

    def _initiate_sagemaker_session(self):
        iam = boto3.client('iam')
        response = iam.list_roles()
        sagemaker_roles = [role for role in response['Roles'] if 'SageMaker' in role['RoleName']]
        self.sess = sagemaker.Session()
        sagemaker_session_bucket = None
        if sagemaker_session_bucket is None and self.sess is not None:
            sagemaker_session_bucket = self.sess.default_bucket()
        try:
            role = sagemaker.get_execution_role()
        except ValueError:
            iam = boto3.client('iam')
            role = iam.get_role(RoleName=sagemaker_roles[0]['RoleName'])['Role']['Arn']
        self.sess = sagemaker.Session(default_bucket=sagemaker_session_bucket)
        print(f"sagemaker role arn: {role}")
        print(f"sagemaker bucket: {self.sess.default_bucket()}")
        print(f"sagemaker session region: {self.sess.boto_region_name}")

    def _format_text_response_as_prompt(self, train_row):
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"{train_row['user_prompt']}\n"}]
        context_prompt = self.tokenizer.decode(self.tokenizer.apply_chat_template(messages, add_generation_prompt=True))
        prompt = context_prompt + train_row['cleaned_responses_without_citations']
        prompt = re.sub(r'\n+', '\n', prompt)
        return prompt

    def _custom_yi_format_text_response_as_prompt(self, train_row):
        prompt = f'USER:{self.SYSTEM_PROMPT}{train_row["user_prompt"]} ASSISTANT:{train_row["cleaned_responses_without_citations"]}{self.tokenizer.eos_token}'
        prompt = re.sub(r'\n+', '\n', prompt)
        return prompt

    def _create_dataset(self):
        # template dataset to add prompt to each sample
        def template_dataset(sample):
            if self.is_yi_model:
                sample["text"] = f"{self._custom_yi_format_text_response_as_prompt(sample)}"
            else:
                sample["text"] = f"{self._format_text_response_as_prompt(sample)}{self.tokenizer.eos_token}"
            return sample

        dataset = Dataset.from_pandas(self.responses_df)
        dataset = dataset.map(template_dataset)
        # tokenize dataset
        dataset = dataset.map(lambda sample: self.tokenizer(sample["text"]), batched=True, remove_columns=list(dataset.features))
        # chunk dataset
        self.lm_dataset = pack_dataset(dataset, chunk_length=self.total_tokens)  # We use 4096 as the maximum length for packing
        print(f"Total number of samples: {len(self.lm_dataset)}")

    def _generate_finetune_id(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        words_file_path = os.path.join(script_dir, 'words.txt')
        with open(words_file_path, 'r') as f:
            words = f.read()
        words = words.split('\n')
        self.finetune_id = ''.join(np.random.choice(words, 3))
        print(f'finetune_id is {self.finetune_id}')

    def _generate_finetune_config(self):
        self._generate_finetune_id()
        self.finetune_dataset_config = {'finetune_id': f'{self.model_id}-search-{self.finetune_id}',
                                        'date': datetime.strftime(datetime.today(), '%Y-%b-%d'),
                                        'num_datapoints': len(self.responses_df),
                                        'data_source': 'gpt4',
                                        'prompt': self.SYSTEM_PROMPT}

    def _upload_dataset_to_s3(self):
        # save train_dataset to s3
        training_input_path = f's3://{self.sess.default_bucket()}/fine_tuning_datasets/{self.finetune_dataset_config["date"]}-{self.finetune_dataset_config["finetune_id"]}'
        self.lm_dataset.save_to_disk(training_input_path)
        print(f"training dataset to: {training_input_path}")
