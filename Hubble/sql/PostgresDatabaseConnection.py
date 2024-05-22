import psycopg2
import os
from psycopg2.pool import ThreadedConnectionPool
import numpy as np
from psycopg2.extensions import register_adapter, AsIs


class PostgresDatabaseConnection:
    _instance = None
    _pool = None

    MIN_CONNS = 1
    MAX_CONNS = 10

    def __new__(cls, db='ml'):

        # Connection parameters
        db_params = {
            "host": os.environ.get("DB_HOST"),
            "port": os.environ.get("DB_PORT"),
            "dbname": os.environ.get("DB_NAME"),
            "user": os.environ.get("DB_USER"),
            "password": os.environ.get("DB_PASSWORD"),
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }

        if db == 'user':
            db_params = {
                "host": os.environ.get("USER_DB_HOST"),
                "port": os.environ.get("USER_DB_PORT"),
                "dbname": os.environ.get("USER_DB_NAME"),
                "user": os.environ.get("USER_DB_USER"),
                "password": os.environ.get("USER_DB_PASSWORD"),
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
            }

        if cls._instance is None:
            cls._instance = super(PostgresDatabaseConnection, cls).__new__(cls)
            # cls._instance.connection = psycopg2.connect(
            if cls._pool is None:
                cls._pool = ThreadedConnectionPool(
                    cls.MIN_CONNS,
                    cls.MAX_CONNS,
                    **db_params
                    # host=os.environ.get("DB_HOST"),
                    # port=os.environ.get("DB_PORT"),
                    # dbname=os.environ.get("DB_NAME"),
                    # user=os.environ.get("DB_USER"),
                    # password=os.environ.get("DB_PASSWORD")

                )
        return cls._instance

    @classmethod
    def get_connection(cls):
        return cls._pool.getconn()

    @classmethod
    def put_connection(cls, conn):
        cls._pool.putconn(conn)
