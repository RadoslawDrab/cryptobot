from bot import Bot, Symbol

def init():
    bot = Bot([
        Symbol('BTCUSDT', 'Bitcoin', 'USDT'),
    ])
    bot.watch()

if __name__ == '__main__':
    init()
