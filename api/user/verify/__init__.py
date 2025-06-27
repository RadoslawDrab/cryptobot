from flask import request

from main import template, mail, jwt
from utils import get_user_id
from utils.api import ApiEndpoint, ApiStatus
from utils.database import Database

# PATH: /verify
# METHODS: GET
def init(api: ApiEndpoint, path: str, db: Database, **kwargs):
   # Checks if url contains token query
   email_token = request.args.get('token')
   if email_token is not None:
      user_id, expiration = jwt.get_keys(email_token, 'user_id', 'expiration')
      user = db.select('users', 'email', condition=f'uuid = "{user_id}"', one=True)
      # Updates database user to verified
      db.update('users', f'uuid = "{user_id}"', email_verified=1)
      # Returns HTML template
      return template.render('info', title='Email verified', message=f'Email "{user.get('email')}" successfully verified')

   user_id = get_user_id(request, jwt)
   user = db.select('users', 'email', condition=f'uuid = "{user_id}"', one=True)
   # Sends verification email
   mail.send_verification_email(user.get('email'), jwt.generate(60, user_id=user_id))

   raise ApiStatus(200, 'Verification mail sent')