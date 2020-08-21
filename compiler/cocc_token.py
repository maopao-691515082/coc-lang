#coding=utf8

import re

def is_valid_name(name):
    return re.match("^[a-zA-Z_]\w*$", name) is not None and name not in ("nil", "true", "false")
