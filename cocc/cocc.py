#coding=utf8

import sys, getopt, os, shutil

import cocc_util, cocc_token, cocc_mod, cocc_out

def main():
    #定位目录
    THIS_SCRIPT_NAME_SUFFIX = "/compiler/cocc.py"
    this_script_name = os.path.realpath(sys.argv[0])
    assert this_script_name.endswith(THIS_SCRIPT_NAME_SUFFIX)
    coc_dir = this_script_name[: -len(THIS_SCRIPT_NAME_SUFFIX)]

    #解析命令行参数
    try:
        opt_list, args = getopt.getopt(sys.argv[1 :], "v")
    except getopt.GetoptError:
        _show_usage_and_exit()
    opt_map = dict(opt_list)
    if "-v" in opt_map:
        cocc_util.enable_vmode()

    cocc_util.vlog("开始")

    #主模块
    assert len(args) == 1
    main_mod_file = args[0]
    assert main_mod_file.endswith(".coc")
    if not os.path.isfile(main_mod_file):
        cocc_util.exit("主模块代码‘%s’不是一个文件" % main_mod_file)
    main_mod_name = os.path.basename(main_mod_file)[: -4]
    if not cocc_token.is_valid_name(main_mod_name):
        cocc_util.exit("主模块‘%s’不是一个合法标识符" % main_mod_name)

    #模块查找路径
    cocc_mod.set_mod_path([os.path.dirname(main_mod_file), coc_dir + "/lib"])

    #目标输出路径
    cocc_out.set_main_mod_name(main_mod_name)
    cocc_out.set_out_dir("%s/tmp/out/%s" % (coc_dir, main_mod_name))

    cocc_mod.precompile(main_mod_name)

    #todo

if __name__ == "__main__":
    main()
