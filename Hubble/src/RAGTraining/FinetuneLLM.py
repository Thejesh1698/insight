import os
import boto3
import sagemaker
from huggingface_hub import HfFolder
from sagemaker.huggingface import HuggingFace
import sys
sys.path.append("../utils")

class FinetuneLLM:

    def __init__(self, model_id, finetune_id, training_input_path, epochs=2, batch_size=3, learning_rate='2e-4', merge_adapters=False, instance='ml.g5.2xlarge', region='ap-south-1', distributed=False):
        self.hyperparameters = None
        self.huggingface_estimator = None
        self.training_input_path = training_input_path
        self.model_s3_path = ''
        self.region = region
        self.distributed=distributed
        self._initiate_sagemaker_session(region=region)
        self._set_hyperparameters(model_id, epochs, batch_size, learning_rate, merge_adapters)
        self._create_hf_estimator(finetune_id=finetune_id, instance=instance)
        self._start_training()

    def _set_hyperparameters(self, model_id, epochs, batch_size, learning_rate, merge_adapters):
        self.hyperparameters = {
            'model_id': model_id,  # pre-trained model
            'dataset_path': '/opt/ml/input/data/training',  # path where sagemaker will save training dataset
            'num_train_epochs': epochs,  # number of training epochs
            'per_device_train_batch_size': batch_size,  # batch size for training
            'gradient_accumulation_steps': 1,  # Number of updates steps to accumulate
            'gradient_checkpointing': True,  # save memory but slower backward pass
            'trust_remote_code': True,
            'bf16': True,  # use bfloat16 precision
            'tf32': True,  # use tf32 precision
            'learning_rate': learning_rate,  # learning rate
            'max_grad_norm': 0.3,  # Maximum norm (for gradient clipping)
            'warmup_ratio': 0.03,  # warmup ratio
            "lr_scheduler_type": "cosine_with_restarts",  # learning rate scheduler
            'save_strategy': "epoch",  # save strategy for checkpoints
            "logging_steps": 10,  # log every x steps
            'merge_adapters': merge_adapters,  # wether to merge LoRA into the model (needs more memory)
            'use_flash_attn': True,  # Whether to use Flash Attention
            'output_dir': '/tmp/run'  # output directory, where to save assets during training
        }
        if HfFolder.get_token() is not None:
            self.hyperparameters['hf_token'] = HfFolder.get_token()  # huggingface token to access gated models, e.g. llama 2

    def _initiate_sagemaker_session(self, region):
        boto_session = boto3.Session(region_name=region)
        sess = sagemaker.Session(boto_session=boto_session)
        sagemaker_session_bucket = sess.default_bucket()
        iam = boto3.client('iam', region_name=region)
        hidden_role_name = 'AmazonSageMaker-ExecutionRole-20231030T210397'
        self.role = iam.get_role(RoleName=hidden_role_name)['Role']['Arn']
        self.sess = sagemaker.Session(boto_session=boto_session, default_bucket=sagemaker_session_bucket)
        # response = iam.list_roles()
        # sagemaker_roles = [role for role in response['Roles'] if 'SageMaker' in role['RoleName']]
        # self.sess = sagemaker.Session()
        # sagemaker_session_bucket = None
        # if sagemaker_session_bucket is None and self.sess is not None:
        #     sagemaker_session_bucket = self.sess.default_bucket()
        # try:
        #     self.role = sagemaker.get_execution_role()
        # except ValueError:
        #     iam = boto3.client('iam')
        #     self.role = iam.get_role(RoleName=sagemaker_roles[0]['RoleName'])['Role']['Arn']
        # self.sess = sagemaker.Session(default_bucket=sagemaker_session_bucket)
        print(f"sagemaker role arn: {self.role}")
        print(f"sagemaker bucket: {self.sess.default_bucket()}")
        print(f"sagemaker session region: {self.sess.boto_region_name}")

    def _create_hf_estimator(self, finetune_id, instance):
        job_name = f'huggingface-qlora-{self.hyperparameters["model_id"].replace("/", "-").replace(".", "-")}-{finetune_id}'
        # create the Estimator
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # distribution = {'smdistributed': {'dataparallel': {'enabled': self.distributed}}}
        utils_path = os.path.join(script_dir, 'utils')
        self.huggingface_estimator = HuggingFace(
            entry_point='run_qlora.py',  # train script
            source_dir='../utils/',  # directory which includes all the files needed for training
            instance_type=instance,  # instances type used for the training job
            instance_count=1,  # the number of instances used for training
            max_run=11 * 60 * 60,  # maximum runtime in seconds (days * hours * minutes * seconds)
            base_job_name=job_name,  # the name of the training job
            role=self.role,  # Iam role used in training job to access AWS resources, e.g. S3
            volume_size=50,  # the size of the EBS volume in GB
            transformers_version='4.28',  # the transformers version used in the training job
            pytorch_version='2.0',  # the pytorch_version version used in the training job
            py_version='py310',  # the python version used in the training job
            hyperparameters=self.hyperparameters,  # the hyperparameters passed to the training job
            environment={"HUGGINGFACE_HUB_CACHE": "/tmp/.cache"},  # set env variable to cache models in /tmp
            disable_output_compression=True  # not compress output to save training time and cost
        )

    def _start_training(self):
        data = {'training': self.training_input_path}
        self.huggingface_estimator.fit(data, wait=True)
        self.model_s3_path = self.huggingface_estimator.model_data["S3DataSource"]["S3Uri"]
