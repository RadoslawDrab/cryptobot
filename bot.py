from binance.client import Client
import time

from database import Database
from database.schema import Schema, Table, Column

schema = Schema(name='history', tables=[
    Table(
        name='currency',
        columns=[
            Column('key', 'TEXT', True, True),
            Column('name', 'TEXT'),
            Column('currency', 'TEXT'),
            Column('up_alert', 'REAL'),
            Column('down_alert', 'REAL'),
            Column('price_change_alert', 'REAL')
        ],
        primary_key=('key', False),
    ),
    Table(
        name='history',
        columns=[
            Column('key', 'INTEGER', True, True),
            Column('timestamp', 'INTEGER', not_null=True),
            Column('currency_key', 'TEXT', not_null=True),
        ],
        primary_key=('key', True),
        foreign_keys=[('currency_key', 'currency', 'key')]
    )
])

class Symbol:
    def __init__(self, key: str, name: str | None = None, currency: str = 'USD', up_alert: float | None = None, down_alert: float | None = None, price_change_alert: float | None = None):
        self.key = key
        self.name = name
        self.currency = currency
        self.up_alert = up_alert
        self.down_alert = down_alert
        self.price_change_alert = price_change_alert
        self.price: float | None = None
        self.date: float | None = None
    def set_price(self, price: float):
        self.price = price
        self.date = time.time()

class Bot:
    def __init__(self, symbols: list[Symbol], interval: int = 5):
        self.interval = interval
        self.client = Client()
        self.symbols = symbols
        self.__history: list[Symbol] = []
        self.__db = Database('./history.db', schema)
    def watch(self):
        while True:
            for symbol in self.symbols:
                price = self.__get_price(symbol)
                if not price:
                    continue
                history = self.__history.copy()
                history.reverse()

                price_change = 1 - price / history[0].price if len(history) > 0 else 0.0
                print(f'{symbol.name} ({symbol.key}): {price} {symbol.currency} ({round(price_change * 100, 4)}%)')
                self.__db.insert('history', key=symbol.key, )
                symbol.set_price(price)
                self.__history.append(symbol)
            time.sleep(max(self.interval, 1))
    def __get_price(self, symbol: Symbol):
        try:
            avg_price = self.client.get_avg_price(symbol=symbol.key)
            return float(avg_price['price'])
        except Exception as e:
            print(f'Error getting price for {symbol.name} ({symbol.key}): {e}')
            return None

