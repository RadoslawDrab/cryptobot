import uuid
from flask import request

from utils import check_password
from utils.api import ApiEndpoint, ApiStatus
from utils.database import Database
from main import mail, jwt

# PATH: /token
# METHODS: GET | POST
def init(api: ApiEndpoint, path: str, db: Database, **kwargs):
    def generate_jwt(user_id: uuid.UUID):
        # Generates token which expires in 30 minutes
        token = jwt.generate(30, user_id=user_id)
        # Updates current user token column
        db.update('users', f'uuid = "{user_id}"', token=token)
        return token
    if request.method == 'POST':
        body = ApiEndpoint.get_body(request, 'email', 'password')
        email, password = body.get('email'), body.get('password')
        user = db.query_one(f'SELECT uuid, password, email_verified FROM users WHERE email = "{email}"')

        if user is None:
            raise ApiStatus(404, f"User with '{email}' doesn\'t exist")

        hashed = user.get('password')
        if not check_password(hashed, password):
            raise ApiStatus(401, 'Invalid password')
        if user.get('email_verified') == 0:
            mail.send_verification_email(body.get('email'), generate_jwt(user.get('uuid')))

        return {'token': generate_jwt(user.get('uuid'))}

    # Gets token from 'Authentication' header
    token = request.headers.get('Authentication')
    if token is None:
        raise ApiStatus(400, "'Authentication' header not present")

    user_id, expiration = jwt.get_keys(token, 'user_id', 'expiration')

    # Doesn't create new token if expiration time is greater than 5 minutes
    if not jwt.expires(token, minutes=5):
        return { 'token': token }

    return { 'token': generate_jwt(user_id) }