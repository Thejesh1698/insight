import os
from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder
import numpy as np

# # SSH tunnel configuration
SSH_HOST = os.environ.get('SSH_HOST')
SSH_USER = os.environ.get('SSH_USER')
SSH_KEY_PATH = os.environ.get('SSH_KEY_PATH')
LOCAL_BIND_PORT = np.random.randint(3000, 4000)
#
#
# # MongoDB server configuration
MONGO_HOST = os.environ.get('MONGO_HOST')
MONGO_PORT = 27017
DB_USERNAME = os.environ.get('MONGO_USERNAME')
DB_PASSWORD = os.environ.get('MONGO_PASSWORD')

# db parameters dict
DB_PARAMS = {
    "host": MONGO_HOST,
    "port": MONGO_PORT,
    "username": DB_USERNAME,
    "password": DB_PASSWORD,
}

if os.environ.get('ENVIRONMENT') == 'local':
    DB_PARAMS = {
        "host": '127.0.0.1',
        "port": LOCAL_BIND_PORT,
        "username": DB_USERNAME,
        "password": DB_PASSWORD,
    }


class MongoDatabaseConnection:
    _instance = None
    _client = None
    _tunnel = None

    def __new__(cls):
        if cls._instance is None:
            try:
                cls._instance = super(MongoDatabaseConnection, cls).__new__(cls)

                if os.environ.get('ENVIRONMENT') == 'local':
                    # initiate mongo client via ssh tunneling
                    cls._instance._client = cls._connect_to_mongodb_using_ssh()
                else:
                    # initiate mongo client
                    cls._instance._client = cls._connect_to_mongodb()
            except Exception as e:
                raise Exception(f"Failed to connect to MongoDB: {e}")

        return cls._instance

    @classmethod
    def get_client(cls):
        return cls._instance._client

    @classmethod
    def close_connection(cls):
        if cls._instance._client:
            cls._instance._client.close()
            cls._instance._client = None

        if cls._tunnel:
            cls._tunnel.stop()
            cls._tunnel = None

    @classmethod
    def _establish_tunnel(cls):
        try:
            tunnel = SSHTunnelForwarder(
                (SSH_HOST, 22),
                ssh_username=SSH_USER,
                ssh_pkey=SSH_KEY_PATH,
                remote_bind_address=(MONGO_HOST, MONGO_PORT),
                local_bind_address=('127.0.0.1', LOCAL_BIND_PORT)
            )

            return tunnel
        except Exception as e:
            raise Exception(f"Failed to establish SSH tunnel: {e}")

    @classmethod
    def _connect_to_mongodb(cls):
        try:
            return MongoClient(**DB_PARAMS)
        except ConnectionError as mongo_error:
            raise Exception(f"Failed to connect to MongoDB Connection: {mongo_error}")

    @classmethod
    def _connect_to_mongodb_using_ssh(cls):
        try:
            # start the tunnel
            cls._tunnel = cls._establish_tunnel()
            cls._tunnel.start()

            return MongoClient(
                directConnection=True,
                **DB_PARAMS
            )
        except ConnectionError as mongo_error:
            raise Exception(f"Failed to connect to MongoDB Connection: {mongo_error}")
