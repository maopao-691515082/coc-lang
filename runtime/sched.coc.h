#ifndef SCHED_COC_H
#define SCHED_COC_H

#include "util.coc.h"
#include "concurrent.coc_native_mod.h"

int start_prog(CocArray<__builtins_$_cls_String *> *coc_argv);
ucontext_t *get_sched_ctx();
void register_co(concurrent_$_cls_Coroutine *co);
concurrent_$_cls_Coroutine *get_curr_co();
void switch_to_sched();

#endif
