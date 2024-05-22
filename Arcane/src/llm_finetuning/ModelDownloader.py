import boto3
import os
from transformers import AutoModel, AutoConfig, AutoTokenizer
from huggingface_hub import HfFolder
from peft import AutoPeftModelForCausalLM
import torch


class ModelDownloader:

    def __init__(self, model_s3_path, original_hf_model_id, finetune_id, local_parent_path, region_name, is_adapter=True):
        self.model_path = model_s3_path
        self.model_id = original_hf_model_id
        self.finetune_id = finetune_id
        self.local_root_path = local_parent_path
        self.region_name = region_name
        filename_prefix = '-'.join(self.model_id.split('/')[1].split('-')[:2])  # tekium/OpenHermes-2.5-Mistral-7B becomes OpenHermes-2.5
        if is_adapter:
            self.hf_finetuned_model_name = f'{filename_prefix}-Adapter-Attributes-{self.finetune_id}'
        else:
            self.hf_finetuned_model_name = f'{filename_prefix}-Attributes-{self.finetune_id}'
        self.local_folder_path = f'{self.local_root_path}/{self.hf_finetuned_model_name}/'
        self.s3 = boto3.client('s3')
        self.bucket_name = f'sagemaker-{region_name}-005418323977'

    def download_model(self):
        s3_path = self.model_path.split(self.bucket_name + '/')[1]
        objects = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=s3_path)
        # Download each file in the folder
        for obj in objects.get('Contents', []):
            s3_file_path = obj['Key']
            local_file_path = os.path.join(self.local_folder_path, s3_file_path[len(s3_path):])
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            self.s3.download_file(self.bucket_name, s3_file_path, local_file_path)
            print(f'Downloaded {s3_file_path} to {local_file_path}')

    def upload_model_to_hf(self):
        model = AutoPeftModelForCausalLM.from_pretrained(self.local_folder_path, torch_dtype=torch.float16)
        hub_id = f'WintWealth/{self.hf_finetuned_model_name}'
        model.push_to_hub(hub_id, token=os.environ.get('HF_TOKEN'), private=True)
        tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        tokenizer.push_to_hub(hub_id, token=os.environ.get('HF_TOKEN'), private=True)

    def upload_adapter_to_s3_for_lorax(self):
        prefix = f'lorax/{self.hf_finetuned_model_name}'
        for root, dirs, files in os.walk(self.local_folder_path):
            for file in files:
                local_file_path = os.path.join(root, file)
                s3_object_key = os.path.join(prefix, os.path.relpath(local_file_path, self.local_folder_path))
                self.s3.upload_file(local_file_path, self.bucket_name, s3_object_key)
        print(f'adapter uploaded to {prefix}')
