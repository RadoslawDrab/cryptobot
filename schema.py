from flask import Flask
from utils.api import ApiEndpoint as api, ApiRule as Rule

def get_api(app: Flask):
    return api(
        ['/'],
        app=app,
    )
