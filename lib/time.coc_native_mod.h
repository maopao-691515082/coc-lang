#ifndef TIME_COC_NATIVE_MOD_H
#define TIME_COC_NATIVE_MOD_H

#include "util.coc.h"

coc_long_t time_$_func_time_us();
CocPtr<__builtins_$_cls_String> time_$_func_strftime(__builtins_$_cls_String *fmt, coc_long_t tm);

#endif
