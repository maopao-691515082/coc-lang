#include "sys.coc_native_mod.h"

CocPtr<io_$_cls_File> sys_$_g_stdin;
CocPtr<io_$_cls_File> sys_$_g_stdout;
CocPtr<io_$_cls_File> sys_$_g_stderr;

static void sys_$_init_native_global_var()
{
    sys_$_g_stdin = create_file_from_FILE_ptr(stdin);
    sys_$_g_stdout = create_file_from_FILE_ptr(stdout);
    sys_$_g_stderr = create_file_from_FILE_ptr(stderr);
}
