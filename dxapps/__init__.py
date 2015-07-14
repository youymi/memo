__author__ = 'youymi'

import uuid

def generate_uuid():
    return uuid.uuid1().__str__().replace("-", "")

class Result(object):
    def __init__(self,data, code, msg):
        self.data = data
        self.code = code
        self.msg = msg
