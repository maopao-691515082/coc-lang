#coding=gbk

"""
输出程序
"""

import os
import shutil
import cocc_common
import cocc_module
import cocc_type
import cocc_token

out_dir = None
runtime_dir = None

class _Code:
    class _CodeBlk:
        def __init__(self, code, need_semicolon):
            self.code = code
            self.need_semicolon = need_semicolon

        def __enter__(self):
            pass

        def __exit__(self, exc_type, exc_value, traceback):
            if exc_type is not None:
                return
            assert len(self.code.indent) >= 4
            self.code.indent = self.code.indent[: -4]
            self.code += "}" + (";" if self.need_semicolon else "")

    def __init__(self, file_path_name):
        self.file_path_name = file_path_name
        self.indent = ""
        self.line_list = []
        if file_path_name.endswith(".h"):
            self.header_guard = os.path.basename(file_path_name).replace(".", "_").upper()
        else:
            self.header_guard = None

    def __iadd__(self, line):
        if line.endswith(":") or line.startswith("#"):
            self.line_list.append(line)
        else:
            self.line_list.append(self.indent + line)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            return
        f = open(self.file_path_name, "w")
        if self.header_guard is not None:
            print >> f, "#ifndef %s" % self.header_guard
            print >> f, "#define %s" % self.header_guard
            print >> f
        for line in self.line_list:
            print >> f, line
        if self.header_guard is not None:
            print >> f
            print >> f, "#endif"

    def new_blk(self, title, start_with_blank_line = True):
        if start_with_blank_line:
            self += ""
        if title:
            self += title
        self += "{"
        self.indent += " " * 4
        return self._CodeBlk(self, title and title.startswith("class "))

def _gen_type_code(type):
    if type.is_array:
        return "CocArray<%s > *" % _gen_type_code(type.to_elem_type())
    if type.token.is_reserved:
        assert type.name not in ("null", "literal_byte", "literal_ubyte", "literal_short", "literal_ushort", "literal_int")
        return "coc_%s_t" % type.name
    assert type.is_obj_type and type.module_name is not None
    if type.gtp_list:
        return "%s<%s > *" % (_gen_cls_name(type.get_cls().gcls), ", ".join([_gen_type_code(gtp) for gtp in type.gtp_list]))
    return "%s *" % _gen_cls_name(type.get_cls())

def _gen_type_code_with_shared_ptr(type):
    code = _gen_type_code(type)
    if code.endswith("*"):
        code = "CocPtr<%s >" % code[: -1]
    return code

def _gen_arg_list_code(arg_map, stmt_list):
    code_list = []
    for name, type in arg_map.iteritems():
        code_list.append("%s %sl_%s" %
                         ((_gen_type_code_with_shared_ptr if name in stmt_list.shared_ptr_var_set else _gen_type_code)(type),
                          "&" if type.is_ref else "", name))
    return ", ".join(code_list)

def _gen_literal_str_code(s):
    code_list = []
    for c in s:
        asc = ord(c)
        assert 0 <= asc <= 0xFF
        if asc < 32 or asc > 126 or asc in ('"', "\\"):
            code_list.append("\\%03o" % asc)
        else:
            code_list.append(c)
    return '"%s"' % "".join(code_list)

def _gen_cls_name(cls):
    return "%s_$_cls_%s" % (cls.module.name, cls.name)

def _gen_func_name(func):
    return "%s_$_func_%s" % (func.module.name, func.name)

def _gen_global_var_name(global_var):
    return "%s_$_g_%s" % (global_var.module.name, global_var.name)

def _strip_copy_ptr(code):
    TAIL = ".copy_ptr())"
    if code.endswith(TAIL):
        code = code[: -len(TAIL)] + TAIL.replace(".copy_ptr()", "")
    return code

def _gen_expr_code(expr, is_lvalue = False):
    if expr.op == "as_ref":
        return _gen_expr_code(expr.arg, True)
    if expr.op in cocc_token.ASSIGN_SYM_SET:
        return "(%s %s %s)" % (_gen_expr_code(expr.lvalue, True), expr.op, _gen_expr_code(expr.expr))
    if expr.op in cocc_token.INC_DEC_SYM_SET:
        return "(%s %s)" % (expr.op, _gen_expr_code(expr.lvalue, True))

    expr_code = "(%s)" % _gen_expr_code_impl(expr, is_lvalue)
    return expr_code

def _gen_expr_code_impl(expr, is_lvalue):
    if expr.op == "promote_to_int":
        cast_code = "static_cast<%s>" % _gen_type_code(cocc_type.INT_TYPE)
        expr_code = _gen_expr_code(expr.arg)
        if not expr_code.startswith("(" + cast_code):
            expr_code = cast_code + expr_code
        return expr_code
    if expr.op == "force_convert":
        tp, e = expr.arg
        if tp.is_obj_type and not e.type.is_null:
            assert e.type.is_obj_type
            cast_code = "dynamic_cast<%s>" % _gen_type_code(tp)
            expr_code_fmt = "((%s)%%s)" % _gen_type_code(e.type)
        else:
            cast_code = "static_cast<%s>" % _gen_type_code(tp)
            expr_code_fmt = "%s"
        expr_code = expr_code_fmt % _gen_expr_code(e)
        if not expr_code.startswith("(" + cast_code):
            expr_code = cast_code + expr_code
        return expr_code
    if expr.op in ("neg", "pos", "!", "~"):
        return "%s%s" % ({"neg" : "-", "pos" : "+"}.get(expr.op, expr.op), _gen_expr_code(expr.arg))
    if expr.op == "same_obj":
        ea, eb = expr.arg
        return "is_same_coc_obj(%s, %s)" % (_gen_expr_code(ea), _gen_expr_code(eb))
    if expr.op in cocc_token.BINOCULAR_OP_SYM_SET:
        ea, eb = expr.arg
        return "%s %s %s" % (_gen_expr_code(ea), expr.op, _gen_expr_code(eb))
    if expr.op == "?:":
        ea, eb, ec = expr.arg
        return "%s ? %s : %s" % (_gen_expr_code(ea), _gen_expr_code(eb), _gen_expr_code(ec))
    if expr.op == "call_this.method":
        method, expr_list = expr.arg
        return "method_%s(%s)" % (method.name, ", ".join([_gen_expr_code(e) for e in expr_list]))
    if expr.op == "call_super.method":
        method, expr_list = expr.arg
        return "%s::method_%s(%s)" % (_gen_cls_name(method.cls), method.name, ", ".join([_gen_expr_code(e) for e in expr_list]))
    if expr.op == "this.attr":
        attr = expr.arg
        expr_code = "attr_%s" % attr.name
        if attr.type.is_obj_type and not is_lvalue:
            expr_code += ".copy_ptr()"
        return expr_code
    if expr.op == "super.attr":
        attr = expr.arg
        expr_code = "%s::attr_%s" % (_gen_cls_name(attr.cls), attr.name)
        if attr.type.is_obj_type and not is_lvalue:
            expr_code += ".copy_ptr()"
        return expr_code
    if expr.op == "call_func":
        func, expr_list = expr.arg
        return "%s(%s)" % (_gen_func_name(func), ", ".join([_gen_expr_code(e) for e in expr_list]))
    if expr.op == "global_var":
        global_var = expr.arg
        expr_code = _gen_global_var_name(global_var)
        if expr.type.is_obj_type and "final" not in global_var.decr_set and not is_lvalue:
            expr_code += ".copy_ptr()"
        return expr_code
    if expr.op == "local_var":
        var_name = expr.arg
        expr_code = "l_%s" % var_name
        if expr.type.is_obj_type:
            for stmt_list in reversed(_stmt_list_stack):
                if var_name in stmt_list.var_map:
                    if not is_lvalue:
                        if var_name in stmt_list.refed_var_set:
                            assert var_name in stmt_list.shared_ptr_var_set #被ref过的object var肯定是shared_ptr
                            expr_code += ".copy_ptr()"
                    break
            else:
                raise Exception("Bug")
        return expr_code
    if expr.op == "literal":
        t = expr.arg
        assert t.type.startswith("literal_")
        type = t.type[8 :]
        if type == "str":
            return "literal_str_%d" % id(t)
        if type == "float":
            return "static_cast<%s>(%g)" % (_gen_type_code(cocc_type.FLOAT_TYPE), t.value)
        if type == "double":
            return "%g" % t.value
        if type == "char":
            assert 0 <= t.value <= 0xFF
            if t.value < 32 or t.value > 126 or t.value in ("'", "\\"):
                return "static_cast<%s>('\\%03o')" % (_gen_type_code(cocc_type.CHAR_TYPE), t.value)
            return "static_cast<%s>('%s')" % (_gen_type_code(cocc_type.CHAR_TYPE), chr(t.value))
        if type in ("ulong", "long", "uint", "int"):
            return "static_cast<%s>(%dULL)" % (_gen_type_code(eval("cocc_type.%s_TYPE" % type.upper())), t.value)
        if type == "bool":
            return t.value
        if type == "null":
            return "NULL"
        raise Exception("Bug")
    if expr.op in ("new", "new_array"):
        if expr.op == "new":
            expr_code_list = [_gen_expr_code(e) for e in expr.arg[0]]
            type = expr.type
            assert type.is_obj_type
        elif expr.op == "new_array":
            base_type, size_list = expr.arg
            expr_code_list = [_gen_expr_code(e) for e in size_list if e is not None]
            type = base_type.to_array_type(len(size_list))
        else:
            raise Exception("Bug")
        type_code = _gen_type_code(type)
        assert type_code.endswith("*")
        type_code = type_code[: -1]
        return "make_coc_ptr(new %s(%s))" % (type_code, ", ".join(expr_code_list))
    if expr.op == "this":
        return "this"
    if expr.op == "[]":
        array_expr, idx_expr = expr.arg
        assert array_expr.type.is_array
        expr_code = "%s->elem_at(%s)" % (_gen_expr_code(array_expr), _gen_expr_code(idx_expr))
        if expr.type.is_obj_type and not is_lvalue:
            expr_code += ".copy_ptr()"
        return expr_code
    if expr.op == "array.size":
        array_expr = expr.arg
        assert array_expr.type.is_array
        return "%s->size()" % _strip_copy_ptr(_gen_expr_code(array_expr))
    if expr.op == "to_ldbl":
        return "(long double)%s" % (_gen_expr_code(expr.arg))
    if expr.op == "to_ull":
        return "(unsigned long long)(static_cast<%s>%s)" % (_gen_type_code(cocc_type.ULONG_TYPE), _gen_expr_code(expr.arg))
    if expr.op == "to_ll":
        return "(long long)(static_cast<%s>%s)" % (_gen_type_code(cocc_type.LONG_TYPE), _gen_expr_code(expr.arg))
    if expr.op == "to_cstr":
        assert expr.arg.type == cocc_type.STR_TYPE
        return "%s->data()" % _gen_expr_code(expr.arg)
    if expr.op == "str_format":
        fmt, expr_list = expr.arg
        return "create_coc_string_from_format(%s, %s)" % (_gen_literal_str_code(fmt), ", ".join([_gen_expr_code(e) for e in expr_list]))
    if expr.op == "call_method":
        obj_expr, method, expr_list = expr.arg
        return "%s->method_%s(%s)" % (_gen_expr_code(obj_expr), method.name, ", ".join([_gen_expr_code(e) for e in expr_list]))
    if expr.op == ".":
        obj_expr, attr = expr.arg
        expr_code = "%s->attr_%s" % (_gen_expr_code(obj_expr), attr.name)
        if expr.type.is_obj_type and not is_lvalue:
            expr_code += ".copy_ptr()"
        return expr_code

    raise Exception("Bug")

def _output_booter(main_module_name):
    with _Code(os.path.join(out_dir, "booter.coc.cpp")) as code:
        for header in ("util", "booter"):
            code += '#include "%s.coc.h"' % header
        for m in cocc_module.module_map.itervalues():
            code += '#include "%s.coc_mod.h"' % m.name
        with code.new_blk("void init_coc_mod_literal_str()"):
            for m in cocc_module.module_map.itervalues():
                code += "%s_$_init_literal_str();" % m.name
        with code.new_blk("void init_coc_mod_global_var()"):
            for m in cocc_module.module_map.itervalues():
                code += "%s_$_init_global_var();" % m.name
        with code.new_blk("int coc_main(%s coc_argv)" % _gen_type_code(cocc_type.STR_TYPE.to_array_type(1))):
            code += "return %s_$_func_main(coc_argv);" % main_module_name

def _output_cls(code, module, cls, cpp_guard = None):
    cls_name_code = _gen_cls_name(cls)
    with code.new_blk("class %s : public %s" %
                      (cls_name_code, "CocObj" if cls.base_cls_type is None else _gen_cls_name(cls.base_cls_type.get_cls()))):
        for attr in cls.attr_map.itervalues():
            code += attr.access_ctrl + ":"
            code += "%s attr_%s;" % (_gen_type_code_with_shared_ptr(attr.type), attr.name)

        code += ""
        for method in cls.construct_method:
            access_ctrl = method.access_ctrl
            code += access_ctrl + ":"
            code += "%s(%s);" % (cls_name_code, _gen_arg_list_code(method.arg_map, method.stmt_list))

        code += "private:" if "final" in cls.decr_set else "protected:"
        code += "virtual ~%s();" % cls_name_code
        code += ""

        for method_list in cls.method_map.itervalues():
            for method in method_list:
                code += method.access_ctrl + ":"
                code += ("virtual %s method_%s(%s)%s;" %
                         (_gen_type_code_with_shared_ptr(method.type), method.name, _gen_arg_list_code(method.arg_map, method.stmt_list),
                          " = 0" if "abstract" in method.decr_set else ""))

        code += ""
        for other_cls in module.class_map.itervalues():
            if other_cls is cls or "native" in other_cls.decr_set:
                continue
            code += "friend class %s;" % _gen_cls_name(other_cls)

        code += ""
        code += "friend void %s_$_init_global_var();" % module.name

        code += ""
        for func_list in module.func_map.itervalues():
            assert func_list
            for func in func_list:
                if "public" in func.decr_set and "native" not in func.decr_set:
                    code += "friend %s %s(%s);" % (_gen_type_code_with_shared_ptr(func.type), _gen_func_name(func),
                                                   _gen_arg_list_code(func.arg_map, func.stmt_list))

        if cpp_guard is not None:
            code += ""
            code += "#ifdef %s" % cpp_guard
        code += ""
        for func_list in module.func_map.itervalues():
            assert func_list
            for func in func_list:
                if "public" not in func.decr_set and "native" not in func.decr_set:
                    code += "friend %s %s(%s);" % (_gen_type_code_with_shared_ptr(func.type), _gen_func_name(func),
                                                   _gen_arg_list_code(func.arg_map, func.stmt_list))
        if cpp_guard is not None:
            code += ""
            code += "#endif"

_stmt_list_stack = []

def _output_stmt(code, curr_stmt_list):
    _stmt_list_stack.append(curr_stmt_list)
    _output_stmt_impl(code, curr_stmt_list)
    _stmt_list_stack.pop()

def _output_stmt_impl(code, curr_stmt_list):
    for stmt in curr_stmt_list:
        if stmt.type == "block":
            with code.new_blk(None):
                _output_stmt(code, stmt.stmt_list)
        elif stmt.type in ("break", "continue"):
            code += "%s;" % stmt.type
        elif stmt.type == "return":
            code += "return %s;" % _strip_copy_ptr(_gen_expr_code(stmt.expr))
        elif stmt.type == "for":
            with code.new_blk(None):
                _stmt_list_stack.append(stmt.stmt_list)
                if len(stmt.for_var_map) == 0:
                    for expr in stmt.init_expr_list:
                        code += "%s;" % _strip_copy_ptr(_gen_expr_code(expr))
                else:
                    assert len(stmt.for_var_map) == len(stmt.init_expr_list)
                    for i, (name, type) in enumerate(stmt.for_var_map.iteritems()):
                        code += ("%s l_%s = %s;" %
                                 ((_gen_type_code_with_shared_ptr if name in stmt.stmt_list.shared_ptr_var_set else _gen_type_code)(type),
                                  name, _strip_copy_ptr(_gen_expr_code(stmt.init_expr_list[i]))))
                for_blk_start_line = ("for (; %s; %s)" %
                                      ("" if stmt.judge_expr is None else _gen_expr_code(stmt.judge_expr),
                                       ", ".join([_strip_copy_ptr(_gen_expr_code(expr)) for expr in stmt.loop_expr_list])))
                _stmt_list_stack.pop()
                with code.new_blk(for_blk_start_line):
                    _output_stmt(code, stmt.stmt_list)
        elif stmt.type == "while":
            with code.new_blk("while (%s)" % _gen_expr_code(stmt.expr)):
                _output_stmt(code, stmt.stmt_list)
        elif stmt.type == "do":
            with code.new_blk("do"):
                _output_stmt(code, stmt.stmt_list)
            code += "while (%s);" % _gen_expr_code(stmt.expr)
        elif stmt.type == "if":
            assert len(stmt.if_expr_list) == len(stmt.if_stmt_list_list) > 0
            for i, stmt_list in enumerate(stmt.if_stmt_list_list):
                with code.new_blk("%sif (%s)" % ("" if i == 0 else "else ", _gen_expr_code(stmt.if_expr_list[i])), i == 0):
                    _output_stmt(code, stmt_list)
            if stmt.else_stmt_list is not None:
                with code.new_blk("else", False):
                    _output_stmt(code, stmt.else_stmt_list)
        elif stmt.type == "var":
            type = curr_stmt_list.var_map[stmt.name]
            code += ("%s l_%s = %s;" %
                     ((_gen_type_code_with_shared_ptr if stmt.name in curr_stmt_list.shared_ptr_var_set else _gen_type_code)(type),
                      stmt.name, _strip_copy_ptr(_gen_expr_code(stmt.expr))))
        elif stmt.type == "expr":
            code += "%s;" % _strip_copy_ptr(_gen_expr_code(stmt.expr))
        else:
            raise Exception("Bug")

def _output_module(module):
    has_native_item = module.has_native_item()
    cpp_guard = "%s_COC_MOD_CPP" % module.name.upper()

    with _Code(os.path.join(out_dir, "%s.coc_mod.h" % module.name)) as code:
        code += '#include "util.coc.h"'

        code += ""
        code += "void %s_$_init_literal_str();" % module.name
        code += "void %s_$_init_global_var();" % module.name

        for cls in module.class_map.itervalues():
            code += ""
            if "native" not in cls.decr_set:
                code += "class %s;" % _gen_cls_name(cls)

        code += ""
        for mn in module.dep_module_set:
            if mn != module.name:
                code += '#include "%s.coc_mod.h"' % mn
        if has_native_item:
            code += '#include "%s.coc_native_mod.h"' % module.name

        code += ""
        for func_list in module.func_map.itervalues():
            assert func_list
            for func in func_list:
                if "native" not in func.decr_set and "public" in func.decr_set:
                    code += ("%s %s(%s);" %
                             (_gen_type_code_with_shared_ptr(func.type), _gen_func_name(func),
                              _gen_arg_list_code(func.arg_map, func.stmt_list)))

        code += ""
        code += "#ifdef %s" % cpp_guard
        code += ""
        for func_list in module.func_map.itervalues():
            assert func_list
            for func in func_list:
                if "native" not in func.decr_set and "public" not in func.decr_set:
                    code += ("static %s %s(%s);" %
                             (_gen_type_code_with_shared_ptr(func.type), _gen_func_name(func),
                              _gen_arg_list_code(func.arg_map, func.stmt_list)))
        code += ""
        code += "#endif"

        for cls in module.class_map.itervalues():
            if "native" not in cls.decr_set:
                _output_cls(code, module, cls, cpp_guard)

        code += ""
        code += "#ifndef %s" % cpp_guard
        code += ""
        for global_var in module.global_var_map.itervalues():
            if "native" not in global_var.decr_set and "public" in global_var.decr_set:
                declare_code = "extern "
                if "final" in global_var.decr_set:
                    declare_code += "const "
                declare_code += "%s %s;" % (_gen_type_code_with_shared_ptr(global_var.type), _gen_global_var_name(global_var))
                code += declare_code
        code += ""
        code += "#endif"

    with _Code(os.path.join(out_dir, "%s.coc_mod.cpp" % module.name)) as code:
        code += "#define %s" % cpp_guard
        code += ""
        code += '#include "%s.coc_mod.h"' % module.name
        if has_native_item:
            code += '#include "%s.coc_native_mod.cxx"' % module.name

        code += ""
        str_type_code = _gen_type_code_with_shared_ptr(cocc_type.STR_TYPE)
        for t in module.literal_str_list:
            assert t.type == "literal_str"
            code += "static %s literal_str_%d;" % (str_type_code, id(t))

        with code.new_blk("void %s_$_init_literal_str()" % module.name):
            for t in module.literal_str_list:
                code += "literal_str_%d = create_coc_string_from_literal(%s);" % (id(t), _gen_literal_str_code(t.value))

        code += ""
        for global_var in module.global_var_map.itervalues():
            if "native" not in global_var.decr_set:
                declare_code = ""
                if "public" not in global_var.decr_set:
                    declare_code += "static "
                declare_code += "%s %s;" % (_gen_type_code_with_shared_ptr(global_var.type), _gen_global_var_name(global_var))
                code += declare_code

        with code.new_blk("void %s_$_init_global_var()" % module.name):
            if has_native_item:
                code += "%s_$_init_native_global_var();" % module.name
            for global_var in module.global_var_map.itervalues():
                if "native" not in global_var.decr_set:
                    code += "%s = %s;" % (_gen_global_var_name(global_var), _gen_expr_code(global_var.expr))

        for cls in module.class_map.itervalues():
            if "native" not in cls.decr_set:
                cls_name_code = "%s" % _gen_cls_name(cls)
                init_code_list = ["attr_%s(0)" % attr.name for attr in cls.attr_map.itervalues() if not attr.type.is_obj_type]
                for method in cls.construct_method:
                    if method.super_construct_expr_list is None:
                        method_init_code_list = []
                    else:
                        assert cls.base_cls_type is not None
                        _stmt_list_stack.append(method.stmt_list)
                        method_init_code_list = ["%s(%s)" %
                                                 (_gen_cls_name(cls.base_cls_type.get_cls()),
                                                  ", ".join([_gen_expr_code(e) for e in method.super_construct_expr_list]))]
                        _stmt_list_stack.pop()
                    method_init_code_list += init_code_list
                    init_code = " : %s" % ", ".join(method_init_code_list) if method_init_code_list else ""
                    with code.new_blk("%s::%s(%s)%s" %
                                      (cls_name_code, cls_name_code, _gen_arg_list_code(method.arg_map, method.stmt_list), init_code)):
                        code += ""
                        _output_stmt(code, method.stmt_list)
                        assert not _stmt_list_stack
                with code.new_blk("%s::~%s()" % (cls_name_code, cls_name_code)):
                    if cls.destruct_method is not None:
                        _output_stmt(code, cls.destruct_method.stmt_list)
                        assert not _stmt_list_stack
                for method_list in cls.method_map.itervalues():
                    for method in method_list:
                        if "abstract" not in method.decr_set:
                            with code.new_blk("%s %s::method_%s(%s)" %
                                              (_gen_type_code_with_shared_ptr(method.type), cls_name_code, method.name,
                                               _gen_arg_list_code(method.arg_map, method.stmt_list))):
                                _output_stmt(code, method.stmt_list)
                                assert not _stmt_list_stack

        for func_list in module.func_map.itervalues():
            assert func_list
            for func in func_list:
                if "native" not in func.decr_set:
                    with code.new_blk("%s%s %s(%s)" %
                                      ("" if "public" in func.decr_set else "static ", _gen_type_code_with_shared_ptr(func.type),
                                       _gen_func_name(func), _gen_arg_list_code(func.arg_map, func.stmt_list))):
                        _output_stmt(code, func.stmt_list)
                        assert not _stmt_list_stack

    if has_native_item:
        shutil.copy(os.path.join(module.dir, "%s.coc_native_mod.h" % module.name), out_dir)
        shutil.copy(os.path.join(module.dir, "%s.coc_native_mod.cxx" % module.name), out_dir)

def _copy_runtime():
    for fn in os.listdir(runtime_dir):
        shutil.copy(os.path.join(runtime_dir, fn), out_dir)

def _gen_makefile(main_module_name):
    f = open(os.path.join(out_dir, "Makefile"), "w")
    print >> f, "all:"
    print >> f, ("\tg++ -Wall -pipe -ggdb3 -O2 -fno-strict-aliasing -fPIC -pthread -lrt -rdynamic -Wno-address -Wswitch-default -Wfloat-equal "
                 "-Winvalid-pch -Wvariadic-macros -Wvolatile-register-var -Wcast-align -Wwrite-strings -Wshadow -Wno-deprecated -std=gnu++0x "
                 "-o %s *.cpp" % main_module_name)

def output(main_module_name):
    shutil.rmtree(out_dir, True)
    os.makedirs(out_dir)
    _output_booter(main_module_name)
    for m in cocc_module.module_map.itervalues():
        _output_module(m)
    _copy_runtime()
    _gen_makefile(main_module_name)
