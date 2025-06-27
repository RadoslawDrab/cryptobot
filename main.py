from flask import Flask
from dotenv import load_dotenv
import os

from schema import get_api
from utils import JWT, get_env
from utils.api import ApiStatus
from utils.database import Database
from utils.email import Email
from utils.templates import TemplatesHandler, Template

load_dotenv('prod.env' if os.getenv('DEV') == False else 'dev.env')
URL = get_env('URL', default='http://localhost:5000')

app = Flask(__name__)

@app.errorhandler(ApiStatus)
def _(error: ApiStatus):
    return error.status, error.code

api = get_api(app)

db = Database('./data/database.db', 'schema.sql')
template = TemplatesHandler(
    Template('site.info.html', 'info', 'title', 'message'),
    Template('site.password-reset.html', 'password-reset-form', 'error'),
    Template('site.api-tree.html', 'api-tree', 'tree'),
    Template('mail.verify.html', 'verify-mail', 'link'),
    Template('mail.password-reset.html', 'password-reset-mail', 'link')
)
mail = Email(
    smtp_server=get_env('SMTP_SERVER'),
    port=int(get_env('SMTP_PORT', default=465)),
    username=get_env('SMTP_USERNAME'),
    password=get_env('SMTP_PASSWORD'),
    from_email=get_env('SMTP_USERNAME'),
    template=template,
    base_path=URL
)
jwt = JWT(get_env('JWT_SECRET'))

password_check_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%^&*(),.?<>:;-_]).{8,}$'

if __name__ == '__main__':
    api.create_tree(
        db=('Database', 'utils.database', db)
    )
    app.run(debug=get_env('DEBUG'))