#coding=gbk

"""
编译器主模块
"""

import sys
import getopt
import os
import cocc_common
import cocc_module
import cocc_type
import cocc_output

def _show_usage_and_exit():
    cocc_common.exit("使用方法：%s 主模块.coc" % sys.argv[0])

def _find_module_file(module_dir_list, module_name):
    #按目录查找
    for module_dir in module_dir_list:
        module_file_path_name = os.path.join(module_dir, module_name) + ".coc"
        if os.path.exists(module_file_path_name):
            return module_file_path_name
    cocc_common.exit("找不到模块：%s" % module_name)

def main():
    #解析命令行参数
    opt_list, args = getopt.getopt(sys.argv[1 :], "", [])

    if len(args) != 1:
        _show_usage_and_exit()

    #通用目录
    compiler_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    lib_dir = os.path.join(os.path.dirname(compiler_dir), "lib")

    #预处理builtins等模块
    cocc_module.builtins_module = cocc_module.Module(os.path.join(lib_dir, "__builtins.coc"))
    cocc_module.module_map[cocc_module.builtins_module.name] = cocc_module.builtins_module
    cocc_module.module_map["concurrent"] = cocc_module.Module(os.path.join(lib_dir, "concurrent.coc"))

    #先处理主模块
    main_file_path_name = os.path.abspath(args[0])
    if not main_file_path_name.endswith(".coc"):
        cocc_common.exit("非法的主模块文件名[%s]" % main_file_path_name)
    if not os.path.exists(main_file_path_name):
        cocc_common.exit("找不到主模块文件[%s]" % main_file_path_name)
    main_module = cocc_module.Module(main_file_path_name)
    cocc_module.module_map[main_module.name] = main_module

    #模块查找的目录列表
    src_dir = os.path.dirname(main_file_path_name)
    module_dir_list = [src_dir, lib_dir]

    #找到并预编译所有涉及到的模块
    compiling_set = main_module.dep_module_set #需要预编译的模块名集合
    while compiling_set:
        new_compiling_set = set()
        for module_name in compiling_set:
            if module_name in cocc_module.module_map:
                #已预编译过
                continue
            module_file_path_name = _find_module_file(module_dir_list, module_name)
            cocc_module.module_map[module_name] = m = cocc_module.Module(module_file_path_name)
            new_compiling_set |= m.dep_module_set
        compiling_set = new_compiling_set

    #先扩展嵌套typedef，然后单独对typedef的type进行check
    cocc_module.builtins_module.expand_typedef()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.expand_typedef()
    cocc_module.builtins_module.expand_typedef()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.check_type_for_typedef()

    #统一check_type
    cocc_module.builtins_module.check_type()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.check_type()

    #检查重载是否有问题
    cocc_module.builtins_module.check_overload()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.check_overload()

    #主模块main函数检查
    if "main" not in main_module.func_map:
        cocc_common.exit("主模块[%s]没有main函数" % main_module.name)
    main_func_list = main_module.func_map["main"]
    assert main_func_list
    if len(main_func_list) != 1:
        cocc_common.exit("主模块[%s]的main函数禁止重载" % main_module.name)
    main_func = main_func_list[0]
    if main_func.type != cocc_type.INT_TYPE:
        cocc_common.exit("主模块[%s]的main函数返回类型必须为int" % main_module.name)
    if len(main_func.arg_map) != 1:
        cocc_common.exit("主模块[%s]的main函数只能有一个类型为'String[]'的参数" % main_module.name)
    tp = main_func.arg_map.itervalues().next()
    if tp.is_ref or tp.array_dim_count != 1 or tp.to_elem_type() != cocc_type.STR_TYPE:
        cocc_common.exit("主模块[%s]的main函数的参数类型必须为'String[]'" % main_module.name)
    if "public" not in main_func.decr_set:
        cocc_common.exit("主模块[%s]的main函数必须是public的" % main_module.name)

    #检查子类的继承是否合法
    cocc_module.builtins_module.check_sub_class()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.check_sub_class()

    #todo：其他一些模块元素的检查和进一步预处理

    #正式编译各模块
    cocc_module.builtins_module.compile()
    for m in cocc_module.module_map.itervalues():
        if m is not cocc_module.builtins_module:
            m.compile()

    cocc_output.out_dir = os.path.join(src_dir, main_module.name)
    cocc_output.runtime_dir = os.path.join(os.path.dirname(lib_dir), "runtime")
    cocc_output.output(main_module.name)

if __name__ == "__main__":
    main()
