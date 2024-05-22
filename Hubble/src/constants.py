import pytz
from dateutil import tz
import enum

embeddings_endpoint = 'huggingface-pytorch-inference-2023-10-30-13-16-43-720'
timezone = tz.tzoffset('IST', 19800)
INDIAN_SOURCES = ["652d53256a2736f06f46cfcf", "65291b1e9a2fbc229e5f29c9", "6530d40d9a7559d3ec6b9871", "6512cdcad01a9c8e86263e05",
                  "650046bd005149c49201269f", "65558d1f672118037c541088", "6555987996fb32eef21a562b", "655598ab96fb32eef21a562c",
                  "6555992096fb32eef21a562d", "65559d4296fb32eef21a5630", "6560af039952a16bbc397224", "6560b3a49952a16bbc397225",
                  "65768d2e7c73e77fdb13a9b3"]
BACKEND_URL = 'https://yg4syp14u8.execute-api.ap-south-1.amazonaws.com/prod'

class ContentType(enum.Enum):
    article = 'ARTICLE'
    podcast_episode = 'PODCAST_EPISODE'


class SourceType(enum.Enum):
    article = 'ARTICLE'
    podcast = 'PODCAST'
