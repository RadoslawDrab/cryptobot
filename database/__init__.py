import sqlite3
from pathlib import Path
from types import NoneType
from database.schema import Schema, Column, Table

class Database:
    def __init__(self, path: str | Path, schema: Schema, backups_dir: Path = Path('backup')):
        self.path: Path = Path(path)
        self.backup_path: Path = backups_dir
        self.schema = schema
        self.__connection: sqlite3.Connection = sqlite3.connect(self.path, timeout=10)
        self.c: sqlite3.Cursor = self.__connection.cursor()
        # cursor

        self.__init_database()

    def __init_database(self):
        for table in self.schema.tables:
            self.c.execute(table.sql())

    def insert(self, table: str, **kwargs: any):
        sql = self.schema.insert(table, **kwargs)
        self.c.execute(sql)
        self.__connection.commit()
    def close(self):
        self.__connection.close()
    def backup(self, name: str | None = None):
        backup_connection = sqlite3.connect(Path.joinpath(self.backup_path, name or self.path.name))

        def progress(status, remaining: int, total: int):
            return status, remaining, total

        self.__connection.backup(backup_connection, progress=progress)

        return progress
