import tornado.ioloop
import tornado.web
import os.path

def go(*param):
    if param != None :
        print(param)
    else:
        print("None value")

go(None)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        print(self.get_template_path())

        if not self.get_cookie("token"):
            self.set_cookie("token","gogogo")
            self.set_secure_cookie("token2","gogogo2")
        else :
            print(self.get_secure_cookie("token2"))

        self.write("Hello, world %s" % self.get_argument("id", 0))
        print( self.get_argument("id",0))
    def post(self):
        self.get()


class MyFormHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("hello.html")
        # self.write('<html><body>中<form action="/myform" method="POST">'
        #            '<input type="text" name="message">'
        #            '<input type="submit" value="Submit">'
        #            '</form></body></html>')

    def post(self):
        self.check_xsrf_cookie()
        self.set_header("Content-Type", "text/plain")
        self.write("You wrote " + self.get_body_argument("message"))

    def delete(self):
        self.render("hello.html")

if __name__ == "__main__":

    print(os.path.join(os.path.dirname(__file__) , "templates"))
    application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/myform", MyFormHandler)
    ],   cookie_secret="xianxian",
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        xsrf_cookies=True,
        debug=True)
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()