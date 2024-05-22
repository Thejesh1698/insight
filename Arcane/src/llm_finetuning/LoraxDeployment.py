import os
import subprocess
import boto3
import json
import sagemaker
from sagemaker import Model
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer


class LoraxDeployment:
    def __init__(self, model_name, endpoint_name, algorithm_name="lorax", tag="sagemaker", region="ap-south-1", instance_type='ml.g5.2xlarge'):
        self.algorithm_name = algorithm_name
        self.model_name = model_name
        self.endpoint_name = endpoint_name
        self.instance_type = instance_type
        self.tag = tag
        self.region = region
        self.config = {}
        self.account = self.get_aws_account_id()
        boto_session = boto3.Session(region_name=region)
        sess = sagemaker.Session(boto_session=boto_session)
        sagemaker_session_bucket = sess.default_bucket()
        iam = boto3.client('iam', region_name=region)
        hidden_role_name = 'AmazonSageMaker-ExecutionRole-20231030T210397'
        self.role = iam.get_role(RoleName=hidden_role_name)['Role']['Arn']
        self.sess = sagemaker.Session(boto_session=boto_session, default_bucket=sagemaker_session_bucket)
        self.image_uri = f"{self.account}.dkr.ecr.{self.region}.amazonaws.com/{self.algorithm_name}:{self.tag}"
        self.ecr_client = boto3.client('ecr', region_name=self.region)
        self.sagemaker_session_bucket = f'sagemaker-{region}-005418323977'
        self.lorax_predictor = None

    def set_config(self):
        number_of_gpu = 1
        if self.instance_type == 'ml.g5.12xlarge':
            number_of_gpu = 4
        self.config = {
            'HF_MODEL_ID': self.model_name,  # model_id from hf.co/models
            # 'HF_MODEL_QUANTIZE': 'gptq',
            # 'HF_MODEL_REVISION': 'main',
            'SM_NUM_GPUS': json.dumps(number_of_gpu),  # Number of GPU used per replica
            'MAX_INPUT_LENGTH': json.dumps(7168),  # Max length of input text
            'MAX_TOTAL_TOKENS': json.dumps(8192),  # Max length of the generation (including input text)
            'MAX_BATCH_PREFILL_TOKENS': json.dumps(7168),
            'HF_SHARDED': json.dumps(True),
            'HF_MODEL_TRUST_REMOTE_CODE': json.dumps(True),
            'COMPILE': json.dumps(False),
            'ADAPTER_BUCKET': self.sagemaker_session_bucket,
            'DISABLE_CUSTOM_KERNELS': json.dumps(False)
        }
        # Model and Endpoint configuration parameters

    def deploy_lorax(self):
        health_check_timeout = 900
        instance_type = self.instance_type
        endpoint_name = self.endpoint_name
        lorax_model = Model(
            image_uri=self.image_uri,
            role=self.role,
            sagemaker_session=self.sess,
            env=self.config
        )
        self.lorax_predictor = lorax_model.deploy(
            endpoint_name=endpoint_name,
            initial_instance_count=1,
            instance_type=instance_type,
            container_startup_health_check_timeout=health_check_timeout,
            serializer=JSONSerializer(),
            deserializer=JSONDeserializer()
        )

    def get_aws_account_id(self):
        sts_client = boto3.client('sts', region_name=self.region)
        return sts_client.get_caller_identity()["Account"]
    #
    # def ensure_ecr_repository_exists(self):
    #     try:
    #         self.ecr_client.describe_repositories(repositoryNames=[self.algorithm_name])
    #     except self.ecr_client.exceptions.RepositoryNotFoundException:
    #         self.ecr_client.create_repository(repositoryName=self.algorithm_name)
    #
    # def build_docker_image(self):
    #     subprocess.run(["docker", "build", "-t", f"{self.algorithm_name}:{self.tag}", "."], cwd="sagemaker_lorax")
    #
    # def authenticate_docker_to_ecr(self):
    #     login_password = subprocess.check_output(["aws", "ecr", "get-login-password", "--region", self.region])
    #     subprocess.run(["docker", "login", "--username", "AWS", "--password-stdin", f"{self.account}.dkr.ecr.{self.region}.amazonaws.com"], input=login_password)
    #
    # def tag_docker_image(self):
    #     subprocess.run(["docker", "tag", f"{self.algorithm_name}:{self.tag}", self.image_uri])
    #
    # def push_docker_image_to_ecr(self):
    #     subprocess.run(["docker", "push", self.image_uri])
    #
    # def save_image_uri_to_tmp_file(self):
    #     with open("/tmp/image_uri", "w") as file:
    #         file.write(self.image_uri)
    #
    # def deploy(self):
    #     self.ensure_ecr_repository_exists()
    #     self.build_docker_image()
    #     self.authenticate_docker_to_ecr()
    #     self.tag_docker_image()
    #     self.push_docker_image_to_ecr()
    #     self.save_image_uri_to_tmp_file()