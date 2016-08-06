#coding=gbk

"""
语句解析
"""

import cocc_common
import cocc_expr
import cocc_type
import cocc_token

class _Stmt:
    def __init__(self, type, **kw_arg):
        self.type = type
        for k, v in kw_arg.iteritems():
            setattr(self, k, v)

class _StmtList(list):
    def __init__(self, var_map):
        list.__init__(self)
        self.var_map = var_map
        self.shared_ptr_var_set = set()
        self.refed_var_set = set()

    def analyze_non_raw_var(self, stmt_list_stack, super_construct_method = None, super_construct_expr_list = None):
        def find_stmt_list(var_name):
            for stmt_list in reversed(stmt_list_stack):
                if var_name in stmt_list.var_map:
                    return stmt_list
            else:
                raise Exception("Bug")

        def is_raw_ptr_type(expr):
            if expr.op == "literal":
                assert not expr.type.is_null
                if expr.type == cocc_type.STR_TYPE:
                    return True

            if expr.op == "force_convert":
                _, expr_to_convert = expr.arg
                if expr_to_convert.type.is_null:
                    return True

            if expr.op == "local_var":
                var_name = expr.arg
                return var_name not in find_stmt_list(var_name).shared_ptr_var_set

            if expr.op == "global_var":
                global_var = expr.arg
                return "final" in global_var.decr_set

            return False

        def analyze_var_assign(var_name, expr):
            stmt_list = find_stmt_list(var_name)
            if not stmt_list.var_map[var_name].is_obj_type:
                return False
            if var_name in stmt_list.shared_ptr_var_set:
                return False
            if is_raw_ptr_type(expr):
                return False
            stmt_list.shared_ptr_var_set.add(var_name)
            return True

        def analyze_refed_var(expr):
            updated = False

            if (expr.op in ("call_super.method", "call_this.method", "call_func", "new", "call_method", "se_op_method") or
                expr.op.startswith("call_op_method")):
                sub_expr_list = []
                if expr.op == "new":
                    expr_list, method = expr.arg
                    arg_map = method.arg_map
                elif expr.op in ("call_method", "se_op_method") or expr.op.startswith("call_op_method"):
                    obj_expr, callee, expr_list = expr.arg
                    sub_expr_list.append(obj_expr)
                    arg_map = callee.arg_map
                else:
                    callee, expr_list = expr.arg
                    arg_map = callee.arg_map
                sub_expr_list.extend(expr_list)
                assert len(expr_list) == len(arg_map)
                for i, expr in enumerate(expr_list):
                    tp = arg_map.value_at(i)
                    if tp.is_ref:
                        assert expr.op == "as_ref"
                        expr = expr.arg
                        assert expr.is_lvalue
                        if expr.op == "local_var":
                            var_name = expr.arg
                            stmt_list = find_stmt_list(var_name)
                            if var_name not in stmt_list.refed_var_set:
                                stmt_list.refed_var_set.add(var_name)
                                updated = True
                                if expr.type.is_obj_type:
                                    stmt_list.shared_ptr_var_set.add(var_name)
            elif isinstance(expr, _SeExpr):
                sub_expr_list = [expr.lvalue]
                if expr.expr is not None:
                    sub_expr_list.append(expr.expr)
            elif expr.op in ("promote_to_int", "~", "!", "neg", "pos", "array.size", "to_ldbl", "to_ull", "to_ll", "to_cstr", "as_ref"):
                sub_expr_list = [expr.arg]
            elif expr.op == "force_convert":
                sub_expr_list = [expr.arg[1]]
            elif expr.op in cocc_token.BINOCULAR_OP_SYM_SET or expr.op in ("?:", "array[]", "is"):
                sub_expr_list = expr.arg
            elif expr.op == "new_array":
                sub_expr_list = [e for e in expr.arg[1] if e is not None]
            elif expr.op == "str_format":
                sub_expr_list = expr.arg[1]
            elif expr.op == ".":
                sub_expr_list = [expr.arg[0]]
            else:
                assert expr.op in ("super.attr", "this.attr", "global_var", "local_var", "literal", "this")
                return False

            for expr in sub_expr_list:
                if analyze_refed_var(expr):
                    updated = True
            return updated

        stmt_list_stack += (self,)
        if len(stmt_list_stack) == 1:
            #最外层要做一些特殊处理
            assert not self.shared_ptr_var_set and not self.refed_var_set
            for name, tp in self.var_map.iteritems():
                if tp.is_ref and tp.is_obj_type:
                    self.shared_ptr_var_set.add(name)
            if super_construct_method is not None:
                assert super_construct_expr_list is not None
                #假装弄个调用基类方法的表达式
                class CallSuperConstructExpr:
                    pass
                e = CallSuperConstructExpr()
                e.op = "call_super.method"
                e.arg = super_construct_method, super_construct_expr_list
                analyze_refed_var(e)

        updated = False
        while True:
            this_turn_updated = False
            for stmt in self:
                if stmt.type in ("block", "for", "while", "do"):
                    if stmt.type == "for":
                        stmt_list_stack += (stmt.stmt_list,)
                        if len(stmt.for_var_map) == 0:
                            for expr in stmt.init_expr_list:
                                if isinstance(expr, _SeExpr) and expr.lvalue.op == "local_var":
                                    if analyze_var_assign(expr.lvalue.arg, expr.expr):
                                        this_turn_updated = True
                                if expr.op == "se_op_method":
                                    lvalue, _, _ = expr.arg
                                    if lvalue.op == "local_var" and lvalue.arg not in stmt_list.shared_ptr_var_set:
                                        stmt_list.shared_ptr_var_set.add(lvalue.arg)
                                        this_turn_updated = True
                        else:
                            assert len(stmt.for_var_map) == len(stmt.init_expr_list)
                            for i, var_name in enumerate(stmt.for_var_map):
                                if analyze_var_assign(var_name, stmt.init_expr_list[i]):
                                    this_turn_updated = True
                        for expr in stmt.init_expr_list:
                            if analyze_refed_var(expr):
                                this_turn_updated = True
                        if stmt.judge_expr is not None:
                            if analyze_refed_var(stmt.judge_expr):
                                this_turn_updated = True
                        for expr in stmt.loop_expr_list:
                            if isinstance(expr, _SeExpr) and expr.lvalue.op == "local_var":
                                if analyze_var_assign(expr.lvalue.arg, expr.expr):
                                    this_turn_updated = True
                            if expr.op == "se_op_method":
                                lvalue, _, _ = expr.arg
                                if lvalue.op == "local_var" and lvalue.arg not in stmt_list.shared_ptr_var_set:
                                    stmt_list.shared_ptr_var_set.add(lvalue.arg)
                                    this_turn_updated = True
                            if analyze_refed_var(expr):
                                this_turn_updated = True
                        stmt_list_stack = stmt_list_stack[: -1]
                    elif stmt.type in ("while", "do"):
                        if analyze_refed_var(stmt.expr):
                            this_turn_updated = True
                    if stmt.stmt_list.analyze_non_raw_var(stmt_list_stack):
                        this_turn_updated = True
                elif stmt.type == "if":
                    for expr in stmt.if_expr_list:
                        if analyze_refed_var(expr):
                            this_turn_updated = True
                    for stmt_list in stmt.if_stmt_list_list:
                        if stmt_list.analyze_non_raw_var(stmt_list_stack):
                            this_turn_updated = True
                    if stmt.else_stmt_list is not None:
                        if stmt.else_stmt_list.analyze_non_raw_var(stmt_list_stack):
                            this_turn_updated = True
                elif stmt.type == "var":
                    if analyze_var_assign(stmt.name, stmt.expr):
                        this_turn_updated = True
                    if analyze_refed_var(stmt.expr):
                        this_turn_updated = True
                elif stmt.type == "expr":
                    if isinstance(stmt.expr, _SeExpr) and stmt.expr.lvalue.op == "local_var":
                        if analyze_var_assign(stmt.expr.lvalue.arg, stmt.expr.expr):
                            this_turn_updated = True
                    if stmt.expr.op == "se_op_method":
                        lvalue, _, _ = stmt.expr.arg
                        if lvalue.op == "local_var" and lvalue.arg not in stmt_list.shared_ptr_var_set:
                            stmt_list.shared_ptr_var_set.add(lvalue.arg)
                            this_turn_updated = True
                    if analyze_refed_var(stmt.expr):
                        this_turn_updated = True
                else:
                    assert stmt.type in ("break", "continue", "return")

            if this_turn_updated:
                updated = True
            else:
                return updated

class _SeExpr:
    def __init__(self, lvalue, op, expr):
        self.lvalue = lvalue
        self.op = op
        self.expr = expr

def _parse_return(token_list, ret_type, var_map_list, cls, module):
    if token_list.peek().is_sym(";"):
        expr = None
        if not ret_type.is_void:
            token_list.peek().syntax_err("需要表达式")
    else:
        expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, ret_type)
    token_list.pop_sym(";")
    return expr

def _parse_expr_with_se(token_list, var_map_list, cls, module):
    def check_lvalue(lvalue):
        if not lvalue.is_lvalue:
            t.syntax_err("需要左值")
        if lvalue.op == "global_var":
            global_var = lvalue.arg
            if "final" in global_var.decr_set:
                t.syntax_err("全局变量'%s.%s'不可修改" % (global_var.module.name, global_var.name))

    def build_inc_dec_expr(op, lvalue, t):
        assert op in ("++", "--")
        if lvalue.op == "call_op_method":
            _, method, _ = lvalue.arg
            if method.name.startswith("__op_item_"):
                se_op = method.name[10 :]
                if op == "++":
                    assert se_op == "inc"
                else:
                    assert se_op == "dec"
                return lvalue
        check_lvalue(lvalue)
        if lvalue.type.is_obj_type:
            return cocc_expr.build_obj_se_expr(lvalue, t, cls, module)
        if not lvalue.type.can_inc_dec:
            t.syntax_err("类型'%s'不可做'%s'操作" % (lvalue.type, op))
        return _SeExpr(lvalue, op, None)

    t = token_list.peek()
    if t.is_sym and t.value in cocc_token.INC_DEC_SYM_SET:
        #前缀自增自减
        op = t.value
        token_list.pop_sym(op)
        t = token_list.peek()
        return build_inc_dec_expr(op, cocc_expr.parse_expr(token_list, var_map_list, cls, module, None, inc_dec_op = op), t)

    expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, None)
    t = token_list.pop()
    if t.is_sym and t.value in cocc_token.INC_DEC_SYM_SET:
        #后缀自增自减
        op = t.value
        return build_inc_dec_expr(op, expr, t)

    if t.is_sym and t.value in cocc_token.ASSIGN_SYM_SET:
        #赋值
        if expr.op == "call_op_method":
            _, method, _ = expr.arg
            if method.name.startswith("__op_item_"):
                t.syntax_err("需要','或';'")

        lvalue = expr
        check_lvalue(lvalue)

        if t.value != "=" and lvalue.type.is_obj_type:
            assert t.value.endswith("=")
            expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, None)
            return cocc_expr.build_obj_se_expr(lvalue, t, cls, module, expr)

        if t.value != "=":
            assert t.value.endswith("=")
            op = t.value[: -1]

            class _InvalidType(Exception):
                pass

            try:
                if op in ("+", "-", "*", "/"):
                    if not lvalue.type.is_number_type:
                        raise _InvalidType()
                elif op in ("%", "&", "|", "^", "<<", ">>"):
                    if not lvalue.type.is_integer_type:
                        raise _InvalidType()
                else:
                    raise Exception("Bug")

            except _InvalidType:
                t.syntax_err("类型'%s'无法做增量赋值'%s'" % (lvalue.type, t.value))

        op = t.value
        if op in ("<<=", ">>="):
            convert_type = [cocc_type.INT_TYPE, cocc_type.UINT_TYPE]
        else:
            convert_type = lvalue.type
        expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, convert_type)
        return _SeExpr(lvalue, op, expr)

    token_list.revert()
    return expr

def _parse_expr_list_with_se(token_list, var_map_list, cls, module):
    expr_list = []
    while True:
        expr = _parse_expr_with_se(token_list, var_map_list, cls, module)
        expr_list.append(expr)
        if not token_list.peek().is_sym(","):
            return expr_list
        token_list.pop_sym(",")

def _parse_for_prefix(token_list, var_map_list, cls, module):
    token_list.pop_sym("(")

    for_var_map = cocc_common.OrderedDict()
    tp = cocc_type.try_parse_type(token_list, module)
    if tp is None:
        #第一部分为表达式列表
        init_expr_list = []
        if not token_list.peek().is_sym(";"):
            init_expr_list += _parse_expr_list_with_se(token_list, var_map_list + (for_var_map,), cls, module)
    else:
        #第一部分为若干变量定义
        init_expr_list = []
        while True:
            t, name = token_list.pop_name()
            if name in module.dep_module_set:
                t.syntax_err("变量名和导入模块名重复")
            token_list.pop_sym("=")
            expr = cocc_expr.parse_expr(token_list, var_map_list + (for_var_map,), cls, module, tp)
            for_var_map[name] = tp
            init_expr_list.append(expr)
            if token_list.peek().is_sym(";"):
                break
            token_list.pop_sym(",")
    token_list.pop_sym(";")

    if token_list.peek().is_sym(";"):
        #没有第二部分
        judge_expr = None
    else:
        judge_expr = cocc_expr.parse_expr(token_list, var_map_list + (for_var_map,), cls, module, cocc_type.BOOL_TYPE)
    token_list.pop_sym(";")

    loop_expr_list = []
    if not token_list.peek().is_sym(")"):
        loop_expr_list += _parse_expr_list_with_se(token_list, var_map_list + (for_var_map,), cls, module)

    token_list.pop_sym(")")

    return for_var_map, init_expr_list, judge_expr, loop_expr_list

def parse_stmt_list(token_list, module, cls, var_map_list, loop_deep, ret_type):
    assert var_map_list
    stmt_list = _StmtList(var_map_list[-1])
    while True:
        if token_list.peek().is_sym("}"):
            break

        t = token_list.pop()
        if t.is_sym(";"):
            continue
        if t.is_sym("{"):
            #新代码块
            stmt_list.append(_Stmt("block", stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (cocc_common.OrderedDict(),),
                                                                        loop_deep, ret_type)))
            token_list.pop_sym("}")
            continue
        if t.is_reserved and t.value in ("break", "continue"):
            if loop_deep == 0:
                t.syntax_err("循环外的'%s'" % t.value)
            stmt_list.append(_Stmt(t.value))
            continue
        if t.is_reserved("return"):
            expr = _parse_return(token_list, ret_type, var_map_list, cls, module)
            stmt_list.append(_Stmt("return", expr = expr))
            continue
        if t.is_reserved("for"):
            for_var_map, init_expr_list, judge_expr, loop_expr_list = _parse_for_prefix(token_list, var_map_list, cls, module)
            token_list.pop_sym("{")
            for_stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (for_var_map.copy(),), loop_deep + 1, ret_type)
            token_list.pop_sym("}")
            stmt_list.append(_Stmt("for", for_var_map = for_var_map, init_expr_list = init_expr_list, judge_expr = judge_expr,
                                   loop_expr_list = loop_expr_list, stmt_list = for_stmt_list))
            continue
        if t.is_reserved("while"):
            token_list.pop_sym("(")
            expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, cocc_type.BOOL_TYPE)
            token_list.pop_sym(")")
            token_list.pop_sym("{")
            while_stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (cocc_common.OrderedDict(),), loop_deep + 1, ret_type)
            token_list.pop_sym("}")
            stmt_list.append(_Stmt("while", expr = expr, stmt_list = while_stmt_list))
            continue
        if t.is_reserved("do"):
            token_list.pop_sym("{")
            do_stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (cocc_common.OrderedDict(),), loop_deep + 1, ret_type)
            token_list.pop_sym("}")
            t = token_list.pop()
            if not t.is_reserved("while"):
                t.syntax_err("需要'while'")
            token_list.pop_sym("(")
            expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, cocc_type.BOOL_TYPE)
            token_list.pop_sym(")")
            token_list.pop_sym(";")
            stmt_list.append(_Stmt("do", expr = expr, stmt_list = do_stmt_list))
            continue
        if t.is_reserved("if"):
            if_expr_list = []
            if_stmt_list_list = []
            else_stmt_list = None
            while True:
                token_list.pop_sym("(")
                expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, cocc_type.BOOL_TYPE)
                token_list.pop_sym(")")
                token_list.pop_sym("{")
                if_stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (cocc_common.OrderedDict(),), loop_deep, ret_type)
                token_list.pop_sym("}")
                if_expr_list.append(expr)
                if_stmt_list_list.append(if_stmt_list)
                if not token_list.peek().is_reserved("else"):
                    break
                token_list.pop()
                t = token_list.pop()
                if t.is_reserved("if"):
                    continue
                if not t.is_sym("{"):
                    t.syntax_err("需要'{'")
                else_stmt_list = parse_stmt_list(token_list, module, cls, var_map_list + (cocc_common.OrderedDict(),), loop_deep, ret_type)
                token_list.pop_sym("}")
                break
            stmt_list.append(_Stmt("if", if_expr_list = if_expr_list, if_stmt_list_list = if_stmt_list_list, else_stmt_list = else_stmt_list))
            continue

        token_list.revert()
        t = token_list.peek()
        tp = cocc_type.try_parse_type(token_list, module)
        if tp is not None:
            #变量定义
            if tp.is_void:
                t.syntax_err("变量类型不能为void")
            while True:
                t, name = token_list.pop_name()
                if name in module.dep_module_set:
                    t.syntax_err("变量名和导入模块重名")
                for var_map in var_map_list:
                    if name in var_map:
                        t.syntax_err("变量名重定义")
                var_map_list[-1][name] = tp
                token_list.pop_sym("=")
                expr = cocc_expr.parse_expr(token_list, var_map_list, cls, module, tp)
                stmt_list.append(_Stmt("var", name = name, expr = expr))
                if token_list.peek().is_sym(";"):
                    break
                token_list.pop_sym(",")
            token_list.pop_sym(";")
            continue

        #表达式
        expr = _parse_expr_with_se(token_list, var_map_list, cls, module)
        stmt_list.append(_Stmt("expr", expr = expr))
        token_list.pop_sym(";")

    return stmt_list
