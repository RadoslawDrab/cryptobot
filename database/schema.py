from types import NoneType


class Column:
    TYPES: list[str] = ['INTEGER', 'REAL', 'TEXT', 'BLOB', 'NUMERIC']

    def __init__(self, name: str, type: str, unique: bool = False, not_null: bool = False):
        self.name = name
        self.type = type
        self.unique = unique
        self.not_null = not_null

    def __str__(self):
        return f'Column({self.name=}, {self.type=})'


class Table:
    """
    Attributes:
        primary_key (tuple[str, bool]): tuple[KEY_NAME, AUTO_INCREMENT]
        foreign_keys (list[tuple[str, str, str]]): tuple[KEY_NAME, REFERENCE_TABLE_NAME, REFERENCE_KEY]
    """

    def __init__(self, name: str, columns: list[Column], primary_key: tuple[str, bool],
                 foreign_keys: list[tuple[str, str, str]] | None = None):
        """
        Parameters:
            primary_key (tuple[str, bool] | None): tuple[KEY_NAME, AUTO_INCREMENT]
            foreign_keys (list[tuple[str, str, str]]): tuple[KEY_NAME, REFERENCE_TABLE_NAME, REFERENCE_KEY]
        """
        self.name = name
        self.primary_key: tuple[str, bool] = primary_key
        self.foreign_keys: list[tuple[str, str, str]] = foreign_keys or []
        self.columns = columns

    def sql(self):
        for column in self.columns:
            if column.type.upper() not in Column.TYPES:
                raise ValueError(f'Invalid column type: {column}')
        sql = 'CREATE TABLE IF NOT EXISTS "{table_name}" (\n{data},\n{options}\n)'
        data = [
            f'"{column.name}" {column.type.upper()}{' NOT NULL' if column.not_null else ''}{' UNIQUE' if column.unique else ''}'
            for column in self.columns
        ]
        options = [
            f'FOREIGN KEY("{key}") REFERENCES "{ref_table}"("{ref_key}")'
            for key, ref_table, ref_key in self.foreign_keys
        ]
        if self.primary_key:
            options.insert(0, f'PRIMARY KEY("{self.primary_key[0]}"{' AUTOINCREMENT' if self.primary_key[1] else ''})')
        return sql.format(table_name=self.name, data=",\n".join(data), options=",\n".join(options))


class Schema:
    def __init__(self, name: str, tables: list[Table]):
        self.name = name
        for table in tables:
            tables_with_same_name = [table for t in tables if t.name == table.name]
            if len(tables_with_same_name) > 1:
                raise ValueError("Can't create tables with the same names")

        self.tables = tables
    @staticmethod
    def kwargs_valid(table: Table, **kwargs: any) -> tuple[bool, str | None]:
        for key, _ in kwargs.items():
            if not any([column.name == key for column in table.columns]):
                return False, f"Key '{key}' doesn't exist in table '{table.name}'"
        if not any([table.primary_key[0] == key for key, _ in kwargs.items()]):
            return False, f"Primary key '{table.primary_key[0]}' not set"
        return True, None
    def get_table(self, name: str):
        table: list[Table] = [t for t in self.tables if t.name == name]
        if len(table) != 1:
            raise ValueError(f"Table name '{name}' is not valid")
        return table[0]

    def insert(self, table_name: str, **kwargs: any):
        valid, error = Schema.kwargs_valid(self.get_table(table_name), **kwargs)
        if not valid:
            raise ValueError(error)

        keys = [key for key in kwargs.keys()]
        values = [kwargs[key] for key in keys]
        formatted_values = []
        for value in values:
            if isinstance(value, str):
                formatted_values.append(f'"{value}"')
                continue
            elif isinstance(value, NoneType):
                formatted_values.append('NULL')
                continue

            formatted_values.append(str(value))
        return f'INSERT INTO {table_name} ({", ".join(keys)}) VALUES ({", ".join(formatted_values)})'
