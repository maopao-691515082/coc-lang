#coding=utf8

import os, sys, getopt, time

import cocc_common, cocc_token, cocc_module, cocc_output

def main():
    #定位目录
    THIS_SCRIPT_NAME_SUFFIX = "/compiler/cocc.py"
    this_script_name = os.path.realpath(sys.argv[0])
    assert this_script_name.endswith(THIS_SCRIPT_NAME_SUFFIX)
    coc_dir = this_script_name[: -len(THIS_SCRIPT_NAME_SUFFIX)]

    def _show_usage_and_exit():
        print >> sys.stderr, """
coc编译器

使用方法

    python cocc.py OPTIONS MAIN_MODULE_SPEC [ARGS]

各参数说明

    OPTIONS: [-v] [-u] [-o OUT_BIN] [--run]

{v}

{u}

{o}

        --run
            编译后立即执行

        -o和--run至少要指定一个，若都指定，则先输出为可执行程序然后执行

{MAIN_MODULE_SPEC}

    ARGS

        运行模块时的命令行参数，指定--run选项的时候有效，如未指定--run，则不能指定ARGS
""".format(**eval(open(coc_dir + "/compiler/help_dict").read()))
        sys.exit(1)

    try:
        opt_list, args = getopt.getopt(sys.argv[1 :], "vuo:m:", ["run"])
    except getopt.GetoptError:
        _show_usage_and_exit()
    opt_map = dict(opt_list)

    if "-v" in opt_map:
        cocc_common.verbose_mode = True
    cocc_common.verbose_log("开始")

    cocc_module.need_update_git = "-u" in opt_map

    out_bin = opt_map.get("-o")
    if out_bin is not None:
        out_bin = cocc_common.abs_path(out_bin)
    need_run = "--run" in opt_map
    if out_bin is None and not need_run: #至少要指定一种行为
        _show_usage_and_exit()
    cocc_output.out_bin = out_bin
    cocc_output.need_run = need_run

    main_module_name = opt_map.get("-m")
    if main_module_name is None:
        if len(args) < 1:
            _show_usage_and_exit()
        main_module_path = cocc_common.abs_path(args[0])
        if not os.path.isdir(main_module_path):
            cocc_common.exit("无效的主模块路径‘%s’：不存在或不是目录" % main_module_path)
        args_for_run = args[1 :]
    else:
        main_module_path = None
        args_for_run = args[:]
    if not need_run and args_for_run:
        _show_usage_and_exit()
    cocc_output.args_for_run = args_for_run

    compiler_dir = coc_dir + "/compiler"
    std_lib_dir = coc_dir + "/std_lib"
    usr_lib_dir = coc_dir + "/usr_lib"
    tmp_workspace_dir = coc_dir + "/tmp_workspace"
    tmp_out_dir = tmp_workspace_dir + "/tmp_out"
    for d in usr_lib_dir, tmp_workspace_dir, tmp_out_dir:
        if not os.path.exists(d):
            try:
                os.makedirs(d)
            except OSError:
                cocc_common.exit("目录‘%s’创建失败" % d)
        if not os.path.isdir(d):
            cocc_common.exit("‘%s’不是目录" % d)

    first_level_std_module_set = set()
    for fn in os.listdir(std_lib_dir):
        if os.path.isdir(std_lib_dir + "/" + fn):
            if not cocc_token.is_valid_name(fn):
                cocc_common.exit("环境检查失败：标准库模块‘%s’名字不是合法的标识符" % fn)
            if fn.count("_") != (2 if fn.startswith("__") else 0):
                cocc_common.exit("环境检查失败：标准库模块‘%s’名字含有非法的下划线" % fn)
            first_level_std_module_set.add(fn)

    #检查一下几个特殊的标准库模块，必须有
    for mn in cocc_common.STD_LIB_INTERNAL_MODULES:
        if mn not in first_level_std_module_set:
            cocc_common.exit("环境检查失败：标准库模块‘%s’缺失" % mn)

    #对于用户库中的模块，如果不是git地址，则也要满足合法标识符条件，且不能和标准库的冲突
    for fn in os.listdir(usr_lib_dir):
        if os.path.isdir(usr_lib_dir + "/" + fn):
            if "." not in fn:
                if not cocc_token.is_valid_name(fn):
                    cocc_common.exit("环境检查失败：用户库模块‘%s’名字不是合法的标识符" % fn)
                if fn in first_level_std_module_set:
                    cocc_common.exit("环境检查失败：用户库模块‘%s’和标准库同名模块冲突" % fn)

    cocc_module.std_lib_dir = std_lib_dir
    cocc_module.usr_lib_dir = usr_lib_dir

    if main_module_path is not None:
        if main_module_path.startswith(std_lib_dir + "/"):
            main_module_name = main_module_path[len(std_lib_dir) + 1 :]
        elif main_module_path.startswith(usr_lib_dir + "/"):
            main_module_name = main_module_path[len(usr_lib_dir) + 1 :]
        else:
            cocc_common.exit("主模块路径不存在于标准库或用户库‘%s’" % main_module_path)
    try:
        main_module_name = cocc_module.ModuleName(main_module_name)
    except cocc_module.ModuleName.InvalidModuleName:
        cocc_common.exit("非法的主模块全名‘%s’" % main_module_name)
    if any([mnp.startswith("__") for mnp in main_module_name.mnpl]):
        cocc_common.exit("不能使用私有模块作为主模块‘%s’" % main_module_name)

    cocc_common.verbose_log("初始化完毕，主模块‘%s’" % main_module_name)

if __name__ == "__main__":
    main()
