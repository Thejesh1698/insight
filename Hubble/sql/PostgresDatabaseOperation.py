from sql.PostgresDatabaseConnection import PostgresDatabaseConnection


class PostgresDatabaseOperation:
    def __init__(self, db='ml'):
        self.db = db
        self.db_connection_pool = None
        self.connection = None
        self.cursor = None

    def __enter__(self):
        if self.db_connection_pool is None:
            self.db_connection_pool = PostgresDatabaseConnection(db=self.db)
        self.connection = self.db_connection_pool.get_connection()
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.connection.rollback()
        else:
            self.connection.commit()
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.db_connection_pool.put_connection(self.connection)
        return False  # allows exception propagation
