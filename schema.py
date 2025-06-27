from flask import Flask
from utils.api import ApiEndpoint as api, ApiRule as Rule

def get_api(app: Flask):
    return api(
        ['/'],
        [
          api(
              ['user'],
              [
                  api(
                      ['verify']
                  ),
                  api(
                      ['reset'],
                      methods=['GET', 'POST']
                  ),
                  api(
                      ['token'],
                      methods=['GET', 'POST']
                  )
              ],
              methods=['GET', 'POST', 'DELETE', 'PUT']
          )
        ],
        app=app,
    )
