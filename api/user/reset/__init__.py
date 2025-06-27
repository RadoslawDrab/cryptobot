import re
from flask import request

from main import mail, jwt, template, password_check_pattern, password_check_text
from utils import get_user_id, hash_password
from utils.api import ApiEndpoint, ApiStatus
from utils.database import Database

# PATH: /reset
# METHODS: GET | POST
def init(api: ApiEndpoint, path: str, db: Database, **kwargs):
   def render(error: str | None = None):
      return template.render('password-reset-form', error=error or False)
   if request.method == 'POST':
      # Gets 'password' and 'password-confirm' properties from form
      new_password, password_confirm = request.form.get('password'), request.form.get('password-confirm')
      token = request.args.get('token')
      if new_password is None or password_confirm is None:
         return render('Password is missing')
      if new_password != password_confirm:
         return render('Passwords are not the same')
      if re.match(password_check_pattern, new_password) is None:
         return render(f'Password too weak. {password_check_text}')

      user_id = get_user_id(request, jwt, token)

      db.update('users', f'uuid = "{user_id}"', password=hash_password(new_password))

      return template.render('info', title='Password updated', message='Password updated successfully')

   email = request.args.get('email')

   # Renders form if 'email' query parameter is not defined
   if email is None:
      return render()

   # Searches for user based on email account
   user = db.select('users', 'uuid', condition=f'email = "{email}"', one=True)

   if user is None:
      raise ApiStatus(404, f"Email '{email}' not found")

   user_id = user.get('uuid')
   # Generates token which lasts 15 minutes
   token = jwt.generate(15, user_id=user_id)
   # Sends password reset mail
   mail.send_password_reset(email, token)
   raise ApiStatus(200, 'Reset password email sent')