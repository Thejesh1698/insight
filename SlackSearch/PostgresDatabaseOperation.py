from PostgresDatabaseConnection import PostgresDatabaseConnection

db_connection_pool = PostgresDatabaseConnection()


class PostgresDatabaseOperation:
    def __init__(self):
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = db_connection_pool.get_connection()
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.connection.rollback()
        else:
            self.connection.commit()
        self.cursor.close()
        db_connection_pool.put_connection(self.connection)
