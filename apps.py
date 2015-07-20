__author__ = 'youymi'
#!/usr/bin/env python
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import concurrent.futures
import os.path
import re
import unicodedata

import tornado.escape
from tornado import gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado.options import define, options

import bcrypt
import markdown
import dxapps
from dxapps import mysqldb
from dxapps.base import BaseHandler

define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default="127.0.0.1", help="blog database host")
define("mysql_database", default="youymi", help="blog database name")
define("mysql_user", default="youymi", help="blog database user")
define("mysql_password", default="youymi", help="blog database password")


# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/archive", ArchiveHandler),
            (r"/my/notes/archive", RecordArchiveHandler),
            (r"/feed", FeedHandler),
            (r"/entry/([^/]+)", EntryHandler),
            (r"/my/notes/entry/([^/]+)", RecordEntryHandler),
            (r"/compose", ComposeHandler),
            (r"/auth/create", AuthCreateHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/user/create",UserCreateHandler),
            (r"/my/notes",MyNotesHadler),
            (r"/my/notes/compose",MyNotesCreateHandler),
        ]
        settings = dict(
            blog_title=u"youymi.com, 个人备忘录",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            ui_modules={"Entry": EntryModule, "Record": RecordEntryModule},
            xsrf_cookies=True,
            cookie_secret="xianxian",
            login_url="/auth/login",
            debug=True,
        )
        super(Application, self).__init__(handlers, **settings)
        # Have one global connection to the blog DB across all handlers
        self.db = mysqldb.Connection(
            user=options.mysql_user, password=options.mysql_password,
            database=options.mysql_database, host=options.mysql_host
            )


class HomeHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC LIMIT 5")
        if not entries:
            self.redirect("/compose")
            return
        self.render("home.html", entries=entries)


class EntryHandler(BaseHandler):
    def get(self, slug):
        entry = self.db.get("SELECT * FROM entries WHERE slug = %s", (slug,))
        if not entry: raise tornado.web.HTTPError(404)
        self.render("entry.html", entry=entry)

class RecordEntryHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, slug):
        entry = self.db.get("SELECT * FROM record WHERE slug = %s", (slug,))
        if not entry or entry.user_id != self.current_user.id:
            raise tornado.web.HTTPError(404)
        self.render("mynotes/record_entry.html", entry=entry,activeid=None)

class ArchiveHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC")
        self.render("archive.html", entries=entries)


class RecordArchiveHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        entries = self.db.query("SELECT * FROM record  where user_id=%s order by `date` "
                                "desc ",(self.current_user.id,))
        self.render("mynotes/archive.html", entries=entries,activeid="noteList")

class FeedHandler(BaseHandler):
    def get(self):
        entries = self.db.query("SELECT * FROM entries ORDER BY published "
                                "DESC LIMIT 10")
        self.set_header("Content-Type", "application/atom+xml")
        self.render("feed.xml", entries=entries)


class ComposeHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        entry = None
        if id:
            entry = self.db.get("SELECT * FROM entries WHERE id = %s", (id,))
        self.render("compose.html", entry=entry)

    @tornado.web.authenticated
    def post(self):

        id = self.get_argument("id", None)
        title = self.get_argument("title")
        text = self.get_argument("markdown",strip=False)
       # print(text)

        html = markdown.markdown(text)

        if id:
            entry = self.db.get("SELECT * FROM entries WHERE id = %s", (id,))
            if not entry: raise tornado.web.HTTPError(404)
            slug = entry.slug
            self.db.execute(  "UPDATE entries SET title = %s, markdown = %s, html = %s "
                "WHERE id = %s", (title, text, html, int(id)))
        else:
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug.decode())
            slug = "-".join(slug.lower().strip().split())
            if not slug: slug = "entry"
            while True:
                e = self.db.get("SELECT * FROM entries WHERE slug = %s", (slug,))
                if not e: break
                slug += "-2"
            self.db.execute(
                "INSERT INTO entries (author_id,title,slug,markdown,html,"
                "published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                (self.current_user.id, title, slug, text, html))
        self.redirect("/entry/" + slug)


class UserCreateHandler(BaseHandler):
    @gen.coroutine
    def post(self):

        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            bcrypt.gensalt())
        self.db.insert("insert user (id, name, email, password,date) values(%s, %s, %s, %s, now())",
                       (self.generate_id(), self.get_argument("name"), self.get_argument("email"),
                        hashed_password, ))
        self.json({"code": 200,"msg": "successed.. "})


class AuthCreateHandler(BaseHandler):
    def get(self):
        self.render("create_author.html")

    @gen.coroutine
    def post(self):
        if self.any_author_exists():
            raise tornado.web.HTTPError(400, "author already created")

        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
            bcrypt.gensalt())
        author_id = self.db.insert(
            "INSERT INTO authors (email, name, hashed_password) "
            "VALUES (%s, %s, %s)",(self.get_argument("email"), self.get_argument("name"),
            hashed_password))
        #self.set_secure_cookie("token", str(author_id))
        self.redirect(self.get_argument("next", "/"))


class AuthLoginHandler(BaseHandler):


    def get(self):
        # If there are no authors, redirect to the account creation page.
        if not self.any_author_exists():
            self.redirect("/auth/create")
        else:
            self.render("login.html", error=None)

    @gen.coroutine
    def post(self):
        user = self.db.get("SELECT password,id FROM user WHERE (email = %s or phone = %s) ",
                            (self.get_argument("name"), self.get_argument("name")) )
        if not user:
            self.render("login.html", error="用户不存在，您可以注册它(%s)" % (self.get_argument("name", "")))
            return
        hashed_password = yield executor.submit(
            bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password", "")),
            tornado.escape.utf8(user.password))
        #print(hashed_password)
        #print(str(hashed_password))
        if hashed_password.decode() == user.password or user.password == self.get_argument("password", ""):
            self.set_secure_cookie("token", str(user.id))
            self.redirect(self.get_argument("next", "/"))
        else:
            self.render("login.html", error="密码不对哦！")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("token")
        self.redirect(self.get_argument("next", "/"))

class MyNotesHadler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user_id = self.current_user.id
        records = self.db.query("select * from record where user_id = %s limit 10", (user_id,))
        self.render("my_notes.html",records = records, activeid=None)

class MyNotesCreateHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        id = self.get_argument("id", None)
        entry = None
        if id:
            entry = self.db.get("SELECT * FROM record WHERE id = %s", (id,))
        self.render("mynotes/compose.html", entry=entry,activeid="noteNew")

    @tornado.web.authenticated
    def put(self):
        id = self.get_argument("id", None)
        entry = None
        if id:
            entry = self.db.get("SELECT * FROM record WHERE id = %s", (id,))
        self.render("mynotes/form.html", entry=entry)

    @tornado.web.authenticated
    def post(self):

        id = self.get_argument("id", None)
        title = self.get_argument("title")
        text = self.get_argument("markdown",strip=False)
       # print(text)

        html = markdown.markdown(text)

        if id:
            entry = self.db.get("SELECT * FROM record WHERE id = %s", (id,))
            if not entry: raise tornado.web.HTTPError(404)
            slug = entry.slug
            self.db.execute(
                "UPDATE record SET title = %s, markdown = %s, html = %s , `update`=now() "
                "WHERE id = %s", (title, text, html, id))
        else:
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug.decode())
            slug = "-".join(slug.lower().strip().split())
            if not slug: slug = "record"
            while True:
                e = self.db.get("SELECT * FROM record WHERE slug = %s", (slug,))
                if not e: break
                slug += "-2"
            self.db.execute(
                "INSERT INTO record (id,user_id,title,slug,markdown,html,"
                "date) VALUES (%s,%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                (self.generate_id(),self.current_user.id, title, slug, text, html))
        self.redirect("/my/notes/entry/" + slug)


class EntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/entry.html", entry=entry)

class RecordEntryModule(tornado.web.UIModule):
    def render(self, entry):
        return self.render_string("modules/record_entry.html", entry=entry)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
