import os
from openai import OpenAI
client = OpenAI(api_key=os.environ.get('OPENAI_KEY'))



class OpenAISummaryService:

    @staticmethod
    def get_request_args():
        pass