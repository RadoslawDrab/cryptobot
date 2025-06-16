from flask import Flask
from schema import get_api

app = Flask(__name__)

api = get_api(app)



if __name__ == '__main__':
    api.create_tree()
    app.run()