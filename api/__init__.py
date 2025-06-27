import json
from flask import request

from main import template
from utils.api import ApiEndpoint
from utils.database import Database

# PATH: /
# METHODS: GET
def init(api: ApiEndpoint, path: str, db: Database, **kwargs):
   return template.render('api-tree', tree=json.dumps(api.tree, indent=2))