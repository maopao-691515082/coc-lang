#ifndef CONCURRENT_COC_NATIVE_MOD_H
#define CONCURRENT_COC_NATIVE_MOD_H

#include <ucontext.h>

#include "util.coc.h"

#ifndef CONCURRENT_COC_MOD_CPP

const extern coc_uint_t concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE;

#endif

void concurrent_$_init_default_coroutine_stack_size();

class concurrent_$_cls_Coroutine : public CocObj
{
public:
    int method_start();

    int get_ret();
    bool finished();
    ucontext_t *get_ctx();

protected:
    concurrent_$_cls_Coroutine();
    virtual ~concurrent_$_cls_Coroutine();

private:
    virtual int method_run() = 0;

    static void co_entry();

    int m_ret;
    bool m_finished;
    ucontext_t m_ctx;
    char *m_stack;
    coc_uint_t m_stack_size;
};

#endif
