#coding=utf8

import os, sys, time
from StringIO import StringIO

STD_LIB_INTERNAL_MODULES = "__builtins",

verbose_mode = False

def verbose_log(msg):
    if verbose_mode:
        print time.strftime("cocc: [%H:%M:%S]"), msg

def _output_ginst_create_chain(f):
    return #todo
    import cocc_module
    ginst_create_chain = []
    ginst = cocc_module.ginst_being_processed[-1]
    while ginst is not None:
        ginst_create_chain.append(ginst)
        ginst = ginst.ginst_creator
    if not ginst_create_chain:
        return
    print >> f, "泛型实例构造链："
    for ginst in reversed(ginst_create_chain):
        print >> f, ginst.creator_token.pos_desc(), ginst

_ERR_EXIT_CODE = 157

def exit(msg):
    print >> sys.stderr, "错误：" + msg
    _output_ginst_create_chain(sys.stderr)
    print >> sys.stderr
    sys.exit(_ERR_EXIT_CODE)

#warning信息不实时输出，而是记录在set中（顺便去重），在编译之后统一输出
_warning_set = set()
def warning(msg):
    f = StringIO()
    print >> f, "警告：" + msg
    _output_ginst_create_chain(f)
    _warning_set.add(f.getvalue())

def output_all_warning():
    for w in _warning_set:
        print >> sys.stderr, w

class OrderedDict:
    def __init__(self):
        self.l = []
        self.d = {}

    def __iter__(self):
        return iter(self.l)

    def __len__(self):
        return len(self.l)

    def __nonzero__(self):
        return len(self) > 0

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        if k not in self.d:
            self.l.append(k)
        self.d[k] = v

    def itervalues(self):
        for k in self.l:
            yield self.d[k]

    def iteritems(self):
        for k in self.l:
            yield k, self.d[k]

    def key_at(self, idx):
        return self.l[idx]

    def value_at(self, idx):
        return self.d[self.l[idx]]

    def copy(self):
        od = OrderedDict()
        for name in self:
            od[name] = self[name]
        return od

class OrderedSet:
    def __init__(self):
        self.d = OrderedDict()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __nonzero__(self):
        return len(self) > 0

    def add(self, k):
        self.d[k] = None

    def elem_at(self, idx):
        return self.d.key_at(idx)

    def copy(self):
        new_s = OrderedSet()
        new_s.d = self.d.copy()
        return new_s

_id = 0
def new_id():
    global _id
    _id += 1
    return _id

def open_src_file(fn):
    f = open(fn)
    f.seek(0, os.SEEK_END)
    if f.tell() > 1024 ** 2:
        exit("源代码文件[%s]过大" % fn)
    f.seek(0, os.SEEK_SET)
    f_cont = f.read()
    try:
        f_cont.decode("utf8")
    except UnicodeDecodeError:
        exit("源代码文件[%s]不是utf8编码" % fn)
    if "\r" in f_cont:
        warning("源代码文件[%s]含有回车符‘\\r’" % fn)
    f.seek(0, os.SEEK_SET)
    return f

#自定义的abs_path，扩展了一些功能
def abs_path(path):
    if path.startswith("~/"):
        #将~/开头的路径转为对应的HOME路径
        home_path = os.getenv("HOME")
        assert home_path
        path = home_path + path[1 :]
    return os.path.abspath(path)
