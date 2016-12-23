#ifndef SYS_COC_NATIVE_MOD_H
#define SYS_COC_NATIVE_MOD_H

#include "util.coc.h"
#include "io.coc_mod.h"

#ifndef SYS_COC_MOD_CPP

const extern CocPtr<io_$_cls_File> sys_$_g_stdin;
const extern CocPtr<io_$_cls_File> sys_$_g_stdout;
const extern CocPtr<io_$_cls_File> sys_$_g_stderr;

#endif

#endif
