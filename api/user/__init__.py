import datetime
import re
import uuid
from flask import request

from utils.api import ApiEndpoint, ApiStatus
from utils.database import Database
from utils import hash_password, check_password, get_user_id
from main import mail, jwt, password_check_pattern, password_check_text


# PATH: /user
# METHODS: GET | POST | DELETE | PATCH
def init(api: ApiEndpoint, path: str, db: Database, **kwargs):
   user: dict = {}
   user_id: uuid.UUID | str | None = None

   if request.method != 'POST':
      user_id = get_user_id(request, jwt)
      user = db.select('users', condition=f'uuid = "{user_id}"', one=True)
      if user is None:
         raise ApiStatus(404, 'User not found')

   match request.method:
      case 'POST':
         body = ApiEndpoint.get_body(request, 'name', 'email', 'password')
         user_id = str(uuid.uuid4())

         db.insert(
            'users',
            ['uuid', 'name', 'email', 'password', 'created_at'],
            (
               user_id,
               body.get('name'),
               body.get('email'),
               hash_password(body.get('password')),
               datetime.datetime.timestamp(datetime.datetime.now())
            )
         )

         mail.send_verification_email(body.get('email'), jwt.generate(60, user_id=user_id))

         raise ApiStatus(201)
      case 'PATCH':
         body = { key: value for key, value in api.get_body(request).items() if key in ['name', 'email', 'password'] }
         password = body.get('password')
         if password is not None:
            if not re.match(password_check_pattern, password):
               raise ApiStatus(400, password_check_text)
            body.update(password=hash_password(password))

         if body.get('email') is not None:
            body.update(email_verified=0)
         db.update('users', f'uuid = "{user_id}"', **body)
         raise ApiStatus(200, 'User updated')
      case 'DELETE':
         body = api.get_body(request, 'password')
         password = body.get('password')
         if not check_password(user.get('password'), password):
            raise ApiStatus(401, 'Invalid password')

         db.delete('users', f'uuid = "{user_id}"')

         raise ApiStatus(200, 'User deleted')
      case 'GET':
         return user