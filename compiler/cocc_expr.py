#coding=gbk

"""
表达式解析
"""

import cocc_common
import cocc_type
import cocc_token
import cocc_module

_UNARY_OP_SET = set(["~", "!", "neg", "pos", "force_convert"])
_BINOCULAR_OP_SET = cocc_token.BINOCULAR_OP_SYM_SET | set(["is"])
_OP_PRIORITY_LIST = [["?", ":", "?:"],
                     ["||"],
                     ["&&"],
                     ["|"],
                     ["^"],
                     ["&"],
                     ["==", "!=", "is"],
                     ["<", "<=", ">", ">="],
                     ["<<", ">>"],
                     ["+", "-"],
                     ["*", "/", "%"],
                     ["~", "!", "neg", "pos", "force_convert"]]
_OP_PRIORITY_MAP = {}
for _i in xrange(len(_OP_PRIORITY_LIST)):
    for _op in _OP_PRIORITY_LIST[_i]:
        _OP_PRIORITY_MAP[_op] = _i
del _i
del _op

def _promote_to_int(e):
    assert e.type.is_integer_type
    if e.type.name in ("byte", "ubyte", "char", "short", "ushort", "literal_byte", "literal_ubyte", "literal_short", "literal_ushort",
                       "literal_int"):
        e = _Expr("promote_to_int", e, cocc_type.INT_TYPE)
    assert e.type.is_integer_type and e.type.name in ("int", "uint", "long", "ulong")
    return e

class _CantMakeTypeSame(Exception):
    pass

def _make_type_same(ea, eb):
    assert ea.type != eb.type
    if ea.type.is_integer_type and eb.type.is_integer_type:
        if ea.type.can_convert_from(eb.type):
            eb = _Expr("force_convert", (ea.type, eb), ea.type)
        elif eb.type.can_convert_from(ea.type):
            ea = _Expr("force_convert", (eb.type, ea), eb.type)
        else:
            raise _CantMakeTypeSame()
        return _promote_to_int(ea), _promote_to_int(eb)

    if ea.type.is_integer_type:
        ea = _promote_to_int(ea)
    if eb.type.is_integer_type:
        eb = _promote_to_int(eb)

    if ea.type.can_convert_from(eb.type):
        eb = _Expr("force_convert", (ea.type, eb), ea.type)
    elif eb.type.can_convert_from(ea.type):
        ea = _Expr("force_convert", (eb.type, ea), eb.type)
    else:
        raise _CantMakeTypeSame()

    return ea, eb

class _Expr:
    def __init__(self, op, arg, type):
        self.op = op
        self.arg = arg
        self.type = type
        self.is_lvalue = op in ("this.attr", "super.attr", "global_var", "local_var", "array[]", ".")

class _ParseStk:
    #解析表达式时使用的栈
    def __init__(self, start_token, cls, curr_module):
        self.start_token = start_token
        self.cls = cls
        self.curr_module = curr_module
        self.stk = []
        self.op_stk = []

    def push_op(self, op, force_convert_type = None):
        if op == "force_convert":
            assert force_convert_type is not None
        else:
            assert force_convert_type is None
        #弹出所有优先级高的运算
        while self.op_stk:
            if _OP_PRIORITY_MAP[self.op_stk[-1]] > _OP_PRIORITY_MAP[op]:
                self._pop_top_op()
            elif _OP_PRIORITY_MAP[self.op_stk[-1]] < _OP_PRIORITY_MAP[op]:
                break
            else:
                #同优先级看结合性
                if op in _UNARY_OP_SET or op in ("?", ":"):
                    #单目、三目运算符右结合
                    break
                self._pop_top_op()
        if op == "force_convert":
            #类型强转额外压入一个类型对象
            self.op_stk.append(force_convert_type)
            self.op_stk.append(op)
            return
        if op == ":":
            if not self.op_stk or self.op_stk[-1] != "?":
                self.start_token.syntax_err("非法的表达式，存在未匹配'?'的':'")
            self.op_stk[-1] = "?:"
            return
        self.op_stk.append(op)

    def _pop_top_op(self):
        op = self.op_stk.pop()
        if op in _UNARY_OP_SET:
            #单目运算符
            if len(self.stk) < 1:
                self.start_token.syntax_err("非法的表达式")
            e = self.stk.pop()
            if op == "force_convert":
                tp = self.op_stk.pop()
                if not tp.can_force_convert_from(e.type):
                    self.start_token.syntax_err("非法的表达式，存在无效的强制类型转换：'%s'到'%s'" % (e.type, tp))
                self.stk.append(_Expr(op, (tp, e), tp))
            else:
                push_e = False

                if op in ("neg", "pos"):
                    if e.type.is_number_type:
                        if e.type.is_integer_type:
                            e = _promote_to_int(e)
                    elif e.type.is_obj_type and not e.type.is_null:
                        e = _parse_unary_op_method_call(op, self, e)
                        op = "call_op_method"
                    else:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做正负运算" % e.type)
                elif op == "!":
                    if not e.type.is_bool_type:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做'!'运算" % e.type)
                elif op == "~":
                    if e.type.is_integer_type:
                        e = _promote_to_int(e)
                    elif e.type.is_obj_type and not e.type.is_null:
                        e = _parse_unary_op_method_call("inv", self, e)
                        op = "call_op_method"
                    else:
                        self.start_token.syntax_err("非法的表达式：类型'%s'不可做'~'运算" % e.type)
                else:
                    raise Exception("Bug")
                if push_e:
                    self.std.append(e)
                else:
                    self.stk.append(_Expr(op, e, e.type))

        elif op in _BINOCULAR_OP_SET:
            #双目运算符
            if len(self.stk) < 2:
                self.start_token.syntax_err("非法的表达式")
            eb = self.stk.pop()
            ea = self.stk.pop()

            class _InvalidBinocularOp(Exception):
                pass

            try:
                normal_binocular_op = False
                push_e = False

                if op in ("&&", "||"):
                    if not ea.type.is_bool_type or not eb.type.is_bool_type:
                        self.start_token.syntax_err("非法的表达式：运算'%s'的左右分量必须是bool型" % op)
                    tp = cocc_type.BOOL_TYPE
                elif op == "is":
                    if ea.type.is_obj_type and eb.type.is_obj_type:
                        #地址比较
                        pass
                    else:
                        raise _InvalidBinocularOp()
                    tp = cocc_type.BOOL_TYPE
                elif op in ("==", "!="):
                    if ea.type.is_bool_type and eb.type.is_bool_type:
                        pass #bool类型也可直接比较
                    elif ea.type.is_number_type and eb.type.is_number_type:
                        normal_binocular_op = True
                    elif ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null:
                        #对象的==和!=流程比较复杂
                        e = _parse_eq_method_call(op, self, ea, eb)
                        if e is None:
                            raise _InvalidBinocularOp()
                        push_e = True
                    else:
                        raise _InvalidBinocularOp()
                    tp = cocc_type.BOOL_TYPE
                elif op in ("+", "-", "*", "/", "<", ">", "<=", ">="):
                    if ea.type.is_number_type and eb.type.is_number_type:
                        normal_binocular_op = True
                    elif ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null:
                        if op in ("<", ">", "<=", ">="):
                            e = _parse_cmp_method_call(op, self, ea, eb)
                        else:
                            e = _parse_num_op_method_call(op, self, ea, eb)
                        if e is None:
                            raise _InvalidBinocularOp()
                        push_e = True
                    else:
                        raise _InvalidBinocularOp()
                    if op in ("<", ">", "<=", ">="):
                        tp = cocc_type.BOOL_TYPE
                    else:
                        tp = None
                elif op in ("%", "&", "|", "^"):
                    if ea.type.is_integer_type and eb.type.is_integer_type:
                        normal_binocular_op = True
                    elif ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null:
                        e = _parse_num_op_method_call(op, self, ea, eb)
                        if e is None:
                            raise _InvalidBinocularOp()
                        push_e = True
                    else:
                        raise _InvalidBinocularOp()
                    tp = None
                elif op in ("<<", ">>"):
                    if ea.type.is_integer_type and eb.type.is_integer_type:
                        ea = _promote_to_int(ea)
                        eb = _promote_to_int(eb)
                    elif ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null:
                        e = _parse_num_op_method_call(op, self, ea, eb)
                        if e is None:
                            raise _InvalidBinocularOp()
                        push_e = True
                    else:
                        raise _InvalidBinocularOp()
                    tp = ea.type
                else:
                    raise Exception("Bug")

                if normal_binocular_op:
                    assert not push_e
                    if ea.type != eb.type:
                        try:
                            ea, eb = _make_type_same(ea, eb)
                        except _CantMakeTypeSame:
                            raise _InvalidBinocularOp()
                    else:
                        if ea.type.is_integer_type:
                            ea = _promote_to_int(ea)
                        if eb.type.is_integer_type:
                            eb = _promote_to_int(eb)
                    assert ea.type == eb.type
                    if tp is None:
                        tp = ea.type
                if push_e:
                    self.stk.append(e)
                else:
                    assert tp is not None
                    self.stk.append(_Expr(op, (ea, eb), tp))

            except _InvalidBinocularOp:
                self.start_token.syntax_err("非法的表达式：类型'%s'和'%s'无法做'%s'运算" % (ea.type, eb.type, op))

        elif op == "?":
            self.start_token.syntax_err("非法的表达式，存在未匹配':'的'?'")

        elif op == "?:":
            #三目运算符
            if len(self.stk) < 3:
                self.start_token.syntax_err("非法的表达式")
            ec = self.stk.pop()
            eb = self.stk.pop()
            ea = self.stk.pop()
            if not ea.type.is_bool_type:
                self.start_token.syntax_err("非法的表达式：'?:'运算的第一运算分量类型不能是'%s'" % ea.type)
            if eb.type == ec.type:
                #完全一样，则使用此类型
                tp = eb.type
            else:
                #类型不相同，归一化类型
                try:
                    eb, ec = _make_type_same(eb, ec)
                except _CantMakeTypeSame:
                    self.start_token.syntax_err("非法的表达式：'?:'运算的第二、三运算分量类型'%s'和'%s'不兼容" % (eb.type, ec.type))
                tp = eb.type
            self.stk.append(_Expr(op, (ea, eb, ec), tp))

        else:
            raise Exception("Bug")

    def push_expr(self, e):
        self.stk.append(e)

    def finish(self):
        while self.op_stk:
            self._pop_top_op()
        if len(self.stk) != 1:
            self.start_token.syntax_err("非法的表达式")
        return self.stk.pop()

def _is_expr_end(t):
    if t.is_sym:
        if t.value in (set([")", "]", ",", ";"]) | cocc_token.ASSIGN_SYM_SET | cocc_token.INC_DEC_SYM_SET):
            return True
    return False

def _parse_expr_list(token_list, var_map_list, cls, curr_module):
    expr_list = []
    if token_list.peek().is_sym(")"):
        token_list.pop_sym(")")
        return expr_list
    while True:
        expr = parse_expr(token_list, var_map_list, cls, curr_module, None)
        expr_list.append(expr)
        if token_list.peek().is_sym(")"):
            token_list.pop_sym(")")
            return expr_list
        token_list.pop_sym(",")

def _check_arg_list(arg_start_token, expr_list, arg_map, shall_success = False):
    try:
        if len(expr_list) != len(arg_map):
            arg_start_token.syntax_err("需要%d个参数，传入了%d个" % (len(arg_map), len(expr_list)))
        for i, (arg_name, arg_type) in enumerate(arg_map.iteritems()):
            expr = expr_list[i]
            if arg_type.is_ref:
                #引用传递，类型必须一致，且需要其他一些检查，并修改expr_list，标记对应表达式为左值形式
                if expr.type != arg_type or not expr.is_lvalue:
                    arg_start_token.syntax_err("参数#%d：必须为类型'%s'的左值" % (i + 1, arg_type))
                if expr.op == "global_var":
                    global_var = expr.arg
                    if "final" in global_var.decr_set:
                        arg_start_token.syntax_err("参数#%d：向ref形参传递带final属性的全局变量" % (i + 1))
                expr_list[i] = _Expr("as_ref", expr, expr.type)
            else:
                if not arg_type.can_convert_from(expr.type):
                    arg_start_token.syntax_err("参数#%d：无法从类型'%s'转为'%s'" % (i + 1, expr.type, arg_type))
                if arg_type != expr.type:
                    expr_list[i] = _Expr("force_convert", (arg_type, expr), arg_type)
    except SystemExit:
        if shall_success:
            raise Exception("Bug")
        raise

def _match_arg_list(expr_list, arg_map):
    if len(expr_list) != len(arg_map):
        return False, False
    full_matched = True
    for i, (arg_name, arg_type) in enumerate(arg_map.iteritems()):
        expr = expr_list[i]
        if arg_type.is_ref:
            #引用传递，类型必须一致，且需要其他一些检查，并修改expr_list，标记对应表达式为左值形式
            if expr.type != arg_type or not expr.is_lvalue:
                return False, False
            if expr.op == "global_var":
                global_var = expr.arg
                if "final" in global_var.decr_set:
                    return False, False
        else:
            if not arg_type.can_convert_from(expr.type):
                return False, False
            if arg_type != expr.type:
                full_matched = False
    return True, full_matched

_MULTI_CALLEE_FOUND = object()
def _match_callee(arg_start_token, callee_list, expr_list):
    if len(callee_list) == 1:
        callee = callee_list[0]
        _check_arg_list(arg_start_token, expr_list, callee.arg_map)
        return arg_start_token, callee, expr_list

    matched_callee_list = []
    for callee in callee_list:
        matched, full_matched = _match_arg_list(expr_list, callee.arg_map)
        if full_matched:
            assert matched
            _check_arg_list(arg_start_token, expr_list, callee.arg_map, True)
            return arg_start_token, callee, expr_list
        if matched:
            matched_callee_list.append(callee)
    if not matched_callee_list:
        return arg_start_token, None, expr_list
    if len(matched_callee_list) == 1:
        callee = matched_callee_list[0]
        _check_arg_list(arg_start_token, expr_list, callee.arg_map, True)
        return arg_start_token, callee, expr_list

    return arg_start_token, _MULTI_CALLEE_FOUND, expr_list

def _parse_call_expr(token_list, var_map_list, cls, curr_module, callee_list):
    arg_start_token = token_list.peek()
    expr_list = _parse_expr_list(token_list, var_map_list, cls, curr_module)
    return _match_callee(arg_start_token, callee_list, expr_list)

def _parse_method_call(t, method_list, expr_list, cls, curr_module, ret_None_method_if_not_found = False):
    assert method_list
    t, method, expr_list = _match_callee(t, method_list, expr_list)
    if method is None:
        if ret_None_method_if_not_found:
            return None, expr_list
        t.syntax_err("找不到匹配的方法'%s.%s.%s(%s)'" %
                     (method_list[0].cls.module.name, method_list[0].cls.name, method_list[0].name,
                      ", ".join([str(e.type) for e in expr_list])))
    if method is _MULTI_CALLEE_FOUND:
        t.syntax_err("调用'%s.%s.%s(%s)'匹配到多个重载方法" %
                     (method_list[0].cls.module.name, method_list[0].cls.name, method_list[0].name,
                      ", ".join([str(e.type) for e in expr_list])))
    if method.cls.module is not curr_module:
        if method.access_ctrl == "private":
            t.syntax_err("无法访问方法'%s.%s.%s(%s)'：没有权限" %
                         (method.cls.module.name, method.cls.name, method.name,
                          ", ".join([str(tp) for tp in method.arg_map.itervalues()])))
        if method.access_ctrl == "protected":
            if cls is None or not cls.is_sub_cls_of(method.cls):
                t.syntax_err("无法访问方法'%s.%s.%s(%s)'：没有权限" %
                             (method.cls.module.name, method.cls.name, method.name,
                              ", ".join([str(tp) for tp in method.arg_map.itervalues()])))
    return method, expr_list

def _parse_unary_op_method_call(op, parse_stk, e):
    method_name = "__op_" + op
    method_list, attr = e.type.get_cls().get_method_or_attr(method_name, parse_stk.start_token)
    assert attr is None
    assert method_list
    method, expr_list = _parse_method_call(parse_stk.start_token, method_list, [], parse_stk.cls, parse_stk.curr_module)
    assert not expr_list
    return _Expr("call_op_method", (e, method, []), method.type)

def _parse_eq_method_call(op, parse_stk, ea, eb, try_reverse_op = True):
    assert op in ("==", "!=")
    assert ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null
    if ea.type.is_obj_type and not ea.type.is_null:
        obj_cls = ea.type.get_cls()
        for method_name in "__op_eq", "__op_cmp":
            if obj_cls.has_method_or_attr(method_name):
                method_list, attr = obj_cls.get_method_or_attr(method_name, parse_stk.start_token)
                assert attr is None
                assert method_list
                method, expr_list = _parse_method_call(parse_stk.start_token, method_list, [eb], parse_stk.cls, parse_stk.curr_module,
                                                       ret_None_method_if_not_found = True)
                if method is not None:
                    if method.name == "__op_eq":
                        assert method.type == cocc_type.BOOL_TYPE
                        e = _Expr("call_op_method", (ea, method, expr_list), method.type)
                        if op == "!=":
                            e = _Expr("!", e, e.type)
                    else:
                        assert method.name == "__op_cmp"
                        assert method.type == cocc_type.INT_TYPE
                        return _Expr("call_op_method.cmp" + op, (ea, method, expr_list), cocc_type.BOOL_TYPE)
                    return e
    if try_reverse_op and eb.type.is_obj_type and not eb.type.is_null:
        return _parse_eq_method_call(op, parse_stk, eb, ea, try_reverse_op = False)
    else:
        return None

def _parse_cmp_method_call(op, parse_stk, ea, eb, try_reverse_op = True):
    assert op in ("<", ">", "<=", ">=")
    assert ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null
    if ea.type.is_obj_type and not ea.type.is_null:
        obj_cls = ea.type.get_cls()
        if obj_cls.has_method_or_attr("__op_cmp"):
            method_list, attr = obj_cls.get_method_or_attr("__op_cmp", parse_stk.start_token)
            assert attr is None
            assert method_list
            method, expr_list = _parse_method_call(parse_stk.start_token, method_list, [eb], parse_stk.cls, parse_stk.curr_module,
                                                   ret_None_method_if_not_found = True)
            if method is not None:
                assert method.type == cocc_type.INT_TYPE
                return _Expr("call_op_method.cmp" + op, (ea, method, expr_list), cocc_type.BOOL_TYPE)
    if try_reverse_op and eb.type.is_obj_type and not eb.type.is_null:
        return _parse_cmp_method_call({"<" : ">", ">" : "<", "<=" : ">=", ">=" : "<="}[op], parse_stk, eb, ea, try_reverse_op = False)
    else:
        return None

def _parse_num_op_method_call(op, parse_stk, ea, eb, try_reverse_op = True):
    assert op in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>")
    op_name = {"+" : "add", "-" : "sub", "*" : "mul", "/" : "div", "%" : "mod", "&" : "and", "|" : "or", "^" : "xor", "<<" : "shl",
               ">>" : "shr"}[op]
    if not try_reverse_op:
        op_name = "r" + op_name
    assert ea.type.is_obj_type and not ea.type.is_null or eb.type.is_obj_type and not eb.type.is_null
    if ea.type.is_obj_type and not ea.type.is_null:
        obj_cls = ea.type.get_cls()
        method_name = "__op_" + op_name
        if obj_cls.has_method_or_attr(method_name):
            method_list, attr = obj_cls.get_method_or_attr(method_name, parse_stk.start_token)
            assert attr is None
            assert method_list
            method, expr_list = _parse_method_call(parse_stk.start_token, method_list, [eb], parse_stk.cls, parse_stk.curr_module,
                                                   ret_None_method_if_not_found = True)
            if method is not None:
                return _Expr("call_op_method" + op, (ea, method, expr_list), method.type)
    if try_reverse_op and eb.type.is_obj_type and not eb.type.is_null:
        return _parse_num_op_method_call(op, parse_stk, eb, ea, try_reverse_op = False)
    else:
        return None

def _parse_method_or_attr_of_this_cls((t, name), token_list, var_map_list, cls, curr_module, is_super = False):
    assert cls is not None
    if is_super:
        assert cls.base_cls_type is not None
        direct_cls = cls.base_cls_type.get_cls()
    else:
        direct_cls = cls
    method_list, attr = direct_cls.get_method_or_attr(name, t)

    if method_list is not None:
        assert attr is None
        assert method_list

        token_list.pop_sym("(")
        expr_list = _parse_expr_list(token_list, var_map_list, cls, curr_module)

        method, expr_list = _parse_method_call(t, method_list, expr_list, cls, curr_module)
        return _Expr("call_super.method" if is_super else "call_this.method", (method, expr_list), method.type)

    assert attr is not None
    assert method_list is None
    if cls is not attr.cls and attr.access_ctrl not in ("public", "protected") and cls.module is not attr.cls.module:
        t.syntax_err("无法访问属性'%s.%s.%s'，没有权限" % (attr.cls.module.name, attr.cls.name, attr.name))
    return _Expr("super.attr" if is_super else "this.attr", attr, attr.type)

def _parse_func_or_global_var(m, (t, name), token_list, var_map_list, cls, curr_module):
    func_list, global_var = m.get_func_or_global_var(name, t)
    if func_list is not None:
        assert global_var is None
        assert func_list

        token_list.pop_sym("(")
        arg_start_token, func, expr_list = _parse_call_expr(token_list, var_map_list, cls, curr_module, func_list)
        if func is None:
            t.syntax_err("找不到匹配的函数'%s.%s(%s)'" % (m.name, name, ", ".join([str(e.type) for e in expr_list])))
        if func is _MULTI_CALLEE_FOUND:
            t.syntax_err("调用'%s.%s(%s)'存在多个重载匹配" % (m.name, name, ", ".join([str(e.type) for e in expr_list])))

        assert func.module is m
        if m is not curr_module and "public" not in func.decr_set:
            t.syntax_err("无法使用函数'%s.%s'：没有权限" % (m.name, name))
        return _Expr("call_func", (func, expr_list), func.type)

    assert global_var is not None
    assert func_list is None
    assert global_var.module is m
    if m is not curr_module and "public" not in global_var.decr_set:
        t.syntax_err("无法使用全局变量'%s.%s'：没有权限" % (m.name, name))
    return _Expr("global_var", global_var, global_var.type)

def parse_expr(token_list, var_map_list, cls, curr_module, convert_type, inc_dec_op = None):
    assert inc_dec_op in (None, "++", "--")
    start_token = token_list.peek()
    parse_stk = _ParseStk(start_token, cls, curr_module)
    while True:
        t = token_list.pop()

        if t.is_sym and t.value in ("~", "!", "+", "-"):
            #单目运算
            if t.value == "+":
                op = "pos"
            elif t.value == "-":
                op = "neg"
            else:
                op = t.value
            parse_stk.push_op(op)
            continue

        if t.is_sym("("):
            tp = cocc_type.try_parse_type(token_list, curr_module)
            if tp is not None:
                #类型强转
                token_list.pop_sym(")")
                parse_stk.push_op("force_convert", tp)
                continue
            #子表达式
            parse_stk.push_expr(parse_expr(token_list, var_map_list, cls, curr_module, None))
            token_list.pop_sym(")")
        elif t.is_name:
            if t.value in curr_module.dep_module_set:
                m = cocc_module.module_map[t.value]
                token_list.pop_sym(".")
                t, name = token_list.pop_name()
                expr = _parse_func_or_global_var(m, (t, name), token_list, var_map_list, cls, curr_module)
                parse_stk.push_expr(expr)
            else:
                for var_map in reversed(var_map_list):
                    if t.value in var_map:
                        #局部变量
                        parse_stk.push_expr(_Expr("local_var", t.value, var_map[t.value]))
                        break
                else:
                    if cls is not None and cls.has_method_or_attr(t.value):
                        #类方法或属性
                        expr = _parse_method_or_attr_of_this_cls((t, t.value), token_list, var_map_list, cls, curr_module)
                        parse_stk.push_expr(expr)
                    else:
                        #当前模块或builtin模块
                        for m in (curr_module, cocc_module.builtins_module):
                            if m.has_func_or_global_var(t.value):
                                expr = _parse_func_or_global_var(m, (t, t.value), token_list, var_map_list, cls, curr_module)
                                parse_stk.push_expr(expr)
                                break
                        else:
                            t.syntax_err("未定义的标识符'%s'" % t.value)
        elif t.is_literal:
            assert t.type.startswith("literal_")
            if t.type == "literal_int":
                for limit, literal_type_name in [(2 ** 7, "byte"), (2 ** 8, "ubyte"), (2 ** 15, "short"), (2 ** 16, "ushort")]:
                    if t.value < limit:
                        type_name = "literal_" + literal_type_name
                        break
                else:
                    assert t.value < 2 ** 31
                    type_name = t.type
            else:
                type_name = t.type[8 :]
            if t.type == "literal_str":
                curr_module.literal_str_list.append(t)
            parse_stk.push_expr(_Expr("literal", t, eval("cocc_type.%s_TYPE" % type_name.upper())))
        elif t.is_reserved("new"):
            base_type = cocc_type.parse_non_array_type(token_list, curr_module.dep_module_set)
            base_type.check(curr_module)
            t = token_list.pop()
            if t.is_sym("("):
                if base_type.token.is_reserved:
                    t.syntax_err("需要'['")
                new_cls = base_type.get_cls()

                abstract_method = new_cls.is_abstract()
                if abstract_method is not None:
                    base_type.token.syntax_err("无法创建抽象类'%s.%s'的实例，未实现抽象方法'%s %s.%s.%s(%s)'" %
                                               (new_cls.module.name, new_cls.name, str(abstract_method.type), abstract_method.cls.module.name,
                                                abstract_method.cls.name, abstract_method.name,
                                                ", ".join([str(tp) for tp in abstract_method.arg_map.itervalues()])))

                arg_start_token, method, expr_list = _parse_call_expr(token_list, var_map_list, cls, curr_module, new_cls.construct_method)
                if method is None:
                    base_type.token.syntax_err("无法创建类'%s.%s'的实例：找不到匹配的构造方法'%s(%s)'" %
                                               (new_cls.module.name, new_cls.name, new_cls.name, ", ".join([str(e.type) for e in expr_list])))
                if method is _MULTI_CALLEE_FOUND:
                    base_type.token.syntax_err("无法创建类'%s.%s'的实例：调用'%s(%s)'匹配到多个构造方法" %
                                               (new_cls.module.name, new_cls.name, new_cls.name, ", ".join([str(e.type) for e in expr_list])))
                if new_cls.module is not curr_module:
                    if method.access_ctrl == "private":
                        base_type.token.syntax_err("无法创建类'%s.%s'的实例：对构造函数'%s(%s)'无访问权限" %
                                                   (new_cls.module.name, new_cls.name, new_cls.name,
                                                    ", ".join([str(tp) for tp in method.arg_map.itervalues()])))
                    if method.access_ctrl == "protected":
                        if cls is None or not cls.is_sub_cls_of(new_cls):
                            base_type.token.syntax_err("无法创建类'%s.%s'的实例：对构造函数'%s(%s)'无访问权限" %
                                                       (new_cls.module.name, new_cls.name, new_cls.name,
                                                        ", ".join([str(tp) for tp in method.arg_map.itervalues()])))
                parse_stk.push_expr(_Expr("new", (expr_list, method), base_type))
            else:
                if not t.is_sym("["):
                    t.syntax_err("需要'['")
                if base_type.is_void:
                    t.syntax_err("无法创建void数组")
                size_list = [parse_expr(token_list, var_map_list, cls, curr_module, cocc_type.LONG_TYPE)]
                init_dim_count = 1
                token_list.pop_sym("]")
                while token_list.peek().is_sym("["):
                    token_list.pop_sym("[")
                    t = token_list.peek()
                    if t.is_sym("]"):
                        size_list.append(None)
                        token_list.pop_sym("]")
                        continue
                    if size_list[-1] is None:
                        t.syntax_err("需要']'")
                    size_list.append(parse_expr(token_list, var_map_list, cls, curr_module, cocc_type.LONG_TYPE))
                    init_dim_count += 1
                    token_list.pop_sym("]")
                parse_stk.push_expr(_Expr("new_array", (base_type, size_list), base_type.to_array_type(len(size_list))))
        elif t.is_reserved("this"):
            if cls is None:
                t.syntax_err("'this'只能用于成员函数中")
            if token_list.peek().is_sym("."):
                token_list.pop_sym(".")
                t, name = token_list.pop_name()
                expr = _parse_method_or_attr_of_this_cls((t, name), token_list, var_map_list, cls, curr_module)
                parse_stk.push_expr(expr)
            else:
                #单独的this
                parse_stk.push_expr(_Expr(t.value, t, cocc_type.gen_type_from_cls(cls)))
        elif t.is_reserved("super"):
            if cls is None or cls.base_cls_type is None:
                t.syntax_err("'super'只能用于子类成员函数中")
            token_list.pop_sym(".")
            t, name = token_list.pop_name()
            expr = _parse_method_or_attr_of_this_cls((t, name), token_list, var_map_list, cls, curr_module, is_super = True)
            parse_stk.push_expr(expr)
        else:
            t.syntax_err("非法的表达式")

        assert parse_stk.stk

        #解析后缀运算符
        while token_list:
            t = token_list.pop()
            if t.is_sym("["):
                obj_expr = parse_stk.stk[-1]
                if obj_expr.type.is_array:
                    expr = parse_expr(token_list, var_map_list, cls, curr_module, cocc_type.LONG_TYPE)
                    token_list.pop_sym("]")
                    parse_stk.stk[-1] = _Expr("array[]", [obj_expr, expr], obj_expr.type.to_elem_type())
                else:
                    if obj_expr.type.token.is_reserved:
                        t.syntax_err("'%s'不能进行下标运算" % obj_expr.type)
                    assert obj_expr.type.is_obj_type
                    obj_cls = obj_expr.type.get_cls()

                    expr = parse_expr(token_list, var_map_list, cls, curr_module, None)
                    token_list.pop_sym("]")

                    #检查下是否是用于副作用表达式
                    if token_list.peek().is_sym and token_list.peek().value in (";", ","):
                        #只有当此下标运算是全表达式末尾时，才考虑inc_dec_op
                        se_op = inc_dec_op
                    else:
                        se_op = None
                    if se_op is None:
                        se_op_token = token_list.peek()
                        if se_op_token.is_sym and se_op_token.value in (cocc_token.ASSIGN_SYM_SET | cocc_token.INC_DEC_SYM_SET):
                            se_op = se_op_token.value

                    #做个转换
                    se_op = {None : "get",
                             "++" : "inc", "--" : "dec",
                             "=" : "set", "%=" : "imod", "^=" : "ixor", "&=" : "iand", "*=" : "imul", "-=" : "isub", "+=" : "iadd",
                             "|=" : "ior", "/=" : "idiv", "<<=" : "ishl", ">>=" : "ishr"}[se_op]

                    #编译为对应方法的调用
                    method_name = "__op_item_" + se_op
                    method_list, attr = obj_cls.get_method_or_attr(method_name, t)
                    assert attr is None
                    assert method_list
                    if se_op in ("get", "inc", "dec"):
                        #取值和元素自增操作
                        expr_list = [expr]
                    else:
                        #赋值类操作
                        token_list.pop_sym()
                        rvalue = parse_expr(token_list, var_map_list, cls, curr_module, None)
                        expr_list = [expr, rvalue]
                    method, expr_list = _parse_method_call(t, method_list, expr_list, cls, curr_module)
                    parse_stk.stk[-1] = _Expr("call_op_method", (obj_expr, method, expr_list), method.type)
            elif t.is_sym("."):
                obj = parse_stk.stk[-1]
                if obj.type.array_dim_count > 0:
                    #数组
                    t, name = token_list.pop_name()
                    if name not in ("size",):
                        t.syntax_err("数组没有'%s'属性" % name)
                    parse_stk.stk[-1] = _Expr("array.size", parse_stk.stk[-1], cocc_type.LONG_TYPE)
                else:
                    if obj.type.token.is_reserved:
                        t.syntax_err("基本类型'%s'无法进行'.'运算" % obj.type)
                    obj_cls = obj.type.get_cls()
                    t, name = token_list.pop_name()
                    if obj.op == "literal" and obj.arg.type == "literal_str" and name == "format":
                        #字符串常量的format语法
                        assert obj.type is cocc_type.STR_TYPE
                        token_list.pop_sym("(")
                        expr_list = _parse_expr_list(token_list, var_map_list, cls, curr_module)
                        fmt = ""
                        pos = 0
                        expr_idx = 0
                        while pos < len(obj.arg.value):
                            if obj.arg.value[pos] != "%":
                                fmt += obj.arg.value[pos]
                                pos += 1
                                continue
                            try:
                                pos += 2
                                conv_spec = obj.arg.value[pos - 1]
                                if conv_spec == "%":
                                    fmt += "%%"
                                    continue
                                if expr_idx >= len(expr_list):
                                    obj.arg.syntax_err("format格式化参数不足")
                                expr = expr_list[expr_idx]
                                expr_idx += 1
                                if conv_spec == "s":
                                    #自动匹配各种情况的默认格式
                                    if expr.type.is_integer_type and expr.type.name == "char":
                                        fmt += "%c"
                                    elif expr.type.is_float_point_type:
                                        fmt += "%Lf"
                                        expr_list[expr_idx - 1] = _Expr("to_ldbl", expr, None)
                                    elif cocc_type.ULONG_TYPE.can_convert_from(expr.type):
                                        fmt += "%llu"
                                        expr_list[expr_idx - 1] = _Expr("to_ull", expr, None)
                                    elif cocc_type.LONG_TYPE.can_convert_from(expr.type):
                                        fmt += "%lld"
                                        expr_list[expr_idx - 1] = _Expr("to_ll", expr, None)
                                    elif expr.type == cocc_type.STR_TYPE:
                                        fmt += "%s"
                                        expr_list[expr_idx - 1] = _Expr("to_cstr", expr, None)
                                    else:
                                        obj.arg.syntax_err("format格式化参数#%d：类型'%s'无法和'%%s'格式匹配" % (expr_idx, expr.type))
                                    continue
                                if conv_spec == "c":
                                    if expr.type.is_integer_type and expr.type.name == "char":
                                        fmt += "%c"
                                    else:
                                        obj.arg.syntax_err("format格式化参数#%d：需要'char'类型" % expr_idx)
                                    continue
                                if conv_spec in ("e", "E", "f", "F", "g", "G"):
                                    if expr.type.is_float_point_type:
                                        fmt += "%L" + conv_spec
                                        expr_list[expr_idx - 1] = _Expr("to_ldbl", expr, None)
                                    else:
                                        obj.arg.syntax_err("format格式化参数#%d：需要浮点数类型" % expr_idx)
                                    continue
                                if conv_spec in ("o", "u", "x", "X"):
                                    if cocc_type.ULONG_TYPE.can_convert_from(expr.type):
                                        fmt += "%ll" + conv_spec
                                        expr_list[expr_idx - 1] = _Expr("to_ull", expr, None)
                                    else:
                                        obj.arg.syntax_err("format格式化参数#%d：需要无符号整数类型" % expr_idx)
                                    continue
                                if conv_spec in ("d", "i"):
                                    if cocc_type.LONG_TYPE.can_convert_from(expr.type):
                                        fmt += "%lld"
                                        expr_list[expr_idx - 1] = _Expr("to_ll", expr, None)
                                    else:
                                        obj.arg.syntax_err("format格式化参数#%d：需要有符号整数类型" % expr_idx)
                                    continue
                                raise IndexError()
                            except IndexError:
                                obj.arg.syntax_err("format格式串错误")
                        if expr_idx < len(expr_list):
                            obj.arg.syntax_err("format格式化参数过多")
                        parse_stk.stk[-1] = _Expr("str_format", (fmt, expr_list), cocc_type.STR_TYPE)
                    else:
                        method_list, attr = obj_cls.get_method_or_attr(name, t)
                        if method_list is not None:
                            assert attr is None
                            assert method_list

                            token_list.pop_sym("(")
                            expr_list = _parse_expr_list(token_list, var_map_list, cls, curr_module)

                            method, expr_list = _parse_method_call(t, method_list, expr_list, cls, curr_module)
                            parse_stk.stk[-1] = _Expr("call_method", (parse_stk.stk[-1], method, expr_list), method.type)
                        else:
                            assert attr is not None
                            assert method_list is None
                            if attr.cls.module is not curr_module:
                                if attr.access_ctrl == "private":
                                    t.syntax_err("无法访问属性'%s.%s.%s'：没有权限" % (attr.cls.module.name, attr.cls.name, attr.name))
                                if attr.access_ctrl == "protected":
                                    if cls is None or not cls.is_sub_cls_of(attr.cls):
                                        t.syntax_err("无法访问属性'%s.%s.%s'：没有权限" % (attr.cls.module.name, attr.cls.name, attr.name))
                            parse_stk.stk[-1] = _Expr(".", (parse_stk.stk[-1], attr), attr.type)
            else:
                token_list.revert()
                break

        if _is_expr_end(token_list.peek()):
            #表达式结束
            break

        #状态：解析普通二元/三元运算符
        t = token_list.pop()
        if t.is_reserved("is") or (t.is_sym and (t.value in _BINOCULAR_OP_SET or t.value in ("?", ":"))):
            #二元运算
            parse_stk.push_op(t.value)
        else:
            t.syntax_err("需要二元或三元运算符")

    expr = parse_stk.finish()
    if convert_type is not None:
        if hasattr(convert_type, "check_convert_from"):
            convert_type_list = [convert_type]
        else:
            convert_type_list = convert_type
        for convert_type in convert_type_list:
            if convert_type == expr.type:
                break
            if convert_type.can_convert_from(expr.type):
                expr = _Expr("force_convert", (convert_type, expr), convert_type)
                break
        else:
            start_token.syntax_err("表达式无法转换为类型%s其中任意一个" % str(convert_type_list))
    return expr

def parse_super_construct_expr_list(method):
    assert method.super_construct_expr_list_token_list
    assert method.cls.base_cls_type
    base_cls = method.cls.base_cls_type.get_cls()

    arg_start_token, base_construct_method, expr_list = (
        _parse_call_expr(method.super_construct_expr_list_token_list, (method.arg_map.copy(),), None, method.cls.module,
                         base_cls.construct_method))
    assert not method.super_construct_expr_list_token_list
    method.super_construct_expr_list_token_list.revert()
    if base_construct_method is None:
        arg_start_token.syntax_err("找不到匹配的基类构造方法'%s.%s.%s(%s)'" %
                                   (base_cls.module.name, base_cls.name, base_cls.name, ", ".join([str(e.type) for e in expr_list])))
    if base_construct_method is _MULTI_CALLEE_FOUND:
        arg_start_token.syntax_err("调用'%s.%s.%s(%s)'匹配到多个基类构造方法" %
                                   (base_cls.module.name, base_cls.name, base_cls.name, ", ".join([str(e.type) for e in expr_list])))
    if base_construct_method.cls.module is not method.cls.module and base_construct_method.access_ctrl not in ("public", "protected"):
        arg_start_token.syntax_err("无法访问基类的构造方法'%s.%s.%s(%s)'：没有权限" %
                                   (base_cls.module.name, base_cls.name, base_cls.name,
                                    ", ".join([str(tp) for tp in base_construct_method.arg_map.itervalues()])))

    return expr_list, base_construct_method

def build_obj_se_expr(lvalue, op_token, cls, curr_module, expr = None):
    assert op_token.is_sym
    op = op_token.value
    assert lvalue.type.is_obj_type and not lvalue.type.is_null
    assert op in (cocc_token.ASSIGN_SYM_SET | cocc_token.INC_DEC_SYM_SET) and op != "="
    if op in cocc_token.INC_DEC_SYM_SET:
        assert expr is None
    else:
        assert expr is not None

    op = {"++" : "inc", "--" : "dec", "%=" : "imod", "^=" : "ixor", "&=" : "iand", "*=" : "imul", "-=" : "isub", "+=" : "iadd", "|=" : "ior",
          "/=" : "idiv", "<<=" : "ishl", ">>=" : "ishr"}[op]

    obj_cls = lvalue.type.get_cls()
    method_list, attr = obj_cls.get_method_or_attr("__op_" + op, op_token)
    assert attr is None
    assert method_list
    method, expr_list = _parse_method_call(op_token, method_list, [] if expr is None else [expr], cls, curr_module)
    return _Expr("se_op_method", (lvalue, method, expr_list), None)
