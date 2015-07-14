__author__ = 'youymi'

import tornado.web
import tornado.escape
import dxapps


class BaseHandler(tornado.web.RequestHandler):

    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        user_id = self.get_secure_cookie("token")
        if not user_id:
            return None
        return self.db.get("SELECT * FROM user WHERE id = %s", (user_id,))

    def any_author_exists(self):
        return bool(self.db.get("SELECT * FROM user LIMIT 1"))

    def generate_id(self):
        return dxapps.generate_uuid()

    def json(self, data=None):
        return self.write(tornado.escape.json_encode(data))

