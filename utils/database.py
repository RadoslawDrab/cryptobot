import re
import sqlite3
from pathlib import Path
from utils.api import ApiStatus

class Database:
    ERROR_CODES = [
        (1, 400, 'Invalid column name'),
        (2067, 400, 'Value is not unique')
    ]
    def __init__(self, path: str | Path, schema_path: str | Path | None = None, dict_return_type: bool = True):
        self.path: Path = Path(path)
        self._check_path(self.path, True)


        self._db: sqlite3.Connection = self.get()
        if dict_return_type:
            self._db.row_factory = sqlite3.Row

        if schema_path is None:
            return
        self.schema_path: Path = Path(schema_path)
        if not self.schema_path.name.endswith('.sql'):
            raise RuntimeError('Schema path is not valid SQL file')


        self._init_schema()
    def _init_schema(self):
        with open(self.schema_path, 'r') as schema_file:
            self._db.executescript(schema_file.read())
            self._db.commit()
    def get(self):
        if not hasattr(self, '_db') or self._db is None:
            Path.mkdir(self.path.parent, exist_ok=True)
            return sqlite3.connect(str(self.path), check_same_thread=False)
        return self._db
    def _execute(self, sql: str):
        try:
            cursor = self._db.execute(sql)
            self._db.commit()
            return cursor
        except sqlite3.Error as e:
            for sql_code, code, message in Database.ERROR_CODES:
                if sql_code == e.sqlite_errorcode:
                    raise ApiStatus(code, message)
            raise ApiStatus(e.sqlite_errorcode, e.sqlite_errorname)

    def insert(self, table: str, columns: list[str] | None = None, *items: tuple):
        values = [f'({", ".join([Database.format(v) for v in item])})' for item in items]
        sql = f'INSERT INTO {table}{f' ({", ".join(columns)})' if columns else ''} VALUES {", ".join(values)};'
        self._execute(sql)
    def update(self, table: str, condition: str, **columns: any):
        sql = f"UPDATE {table} SET {", ".join([f'{column} = {Database.format(value)}' for column, value in columns.items()])} WHERE {condition};"
        self._execute(sql)
    def delete(self, table: str, condition: str):
        sql = f"DELETE FROM {table} WHERE {condition};"
        self._execute(sql)
    def select(self, table: str, *columns: str, condition: str | None = None, distinct: bool = False, order_by: tuple[str, bool] | None = None, one: bool = False) -> list[dict[str, any]] | dict[str, any] | None:
        sql = f"SELECT {'DISTINCT ' if distinct else ''}{", ".join(columns) if len(columns) > 0 else '*' } FROM {table}{f' WHERE {condition}' if condition else ''}{f' ORDER BY {order_by[0]} {'ASC' if order_by[1] else 'DESC'}' if order_by else ''}"
        cur = self._execute(sql)
        rv: list[sqlite3.Row] = cur.fetchall()
        cur.close()
        rows = [{key: row[key] for key in row.keys()} for row in rv]
        return (rows[0] if rows else None) if one else rows
    def query_one(self, query: str, args=()):
        v = self.query(query, args)
        return v[0] if v else None
    def query(self, query: str, args=()):
        cur = self._db.execute(query, args)
        rv: list[sqlite3.Row] = cur.fetchall()
        cur.close()
        return [{ key: row[key]  for key in row.keys() } for row in rv]
    def close(self):
        self._db.close()
    @staticmethod
    def format(value: any):
        if type(value) == str:
            return f'"{value}"'
        if type(value) == int or type(value) == float:
            return f'{value}'
        if type(value) == bool:
            return f'{1 if value else 0}'
        raise ValueError(f'Unsupported type {type(value)}')

    def _check_path(self, path: Path | str, raise_errors: bool = False):
        path = Path(path)
        def error(message: str | None = None):
            if raise_errors and message:
                raise RuntimeError(message)
            return False
        if not path.name.endswith('.db'):
            return error('Invalid database file type')
        return True
