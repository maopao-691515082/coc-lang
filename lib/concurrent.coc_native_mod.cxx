#include "sched.coc.h"
#include "concurrent.coc_native_mod.h"

coc_uint_t concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE;

void concurrent_$_init_default_coroutine_stack_size()
{
    const char *v = getenv("COC_DEFAULT_COROUTINE_STACK_SIZE");
    if (v == NULL)
    {
        concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE = 16 * 1024;
        return;
    }
    int stk_sz = atoi(v);
    if (stk_sz < 4 * 1024 || stk_sz > 64 * 1024 * 1024)
    {
        concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE = 16 * 1024;
        return;
    }
    concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE = (coc_uint_t)stk_sz;
}

static void concurrent_$_init_native_global_var()
{
    coc_assert(concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE >= 4 * 1024 && concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE <= 64 * 1024 * 1024);
}

concurrent_$_cls_Coroutine::concurrent_$_cls_Coroutine()
{
    m_stack_size = concurrent_$_g_DEFAULT_COROUTINE_STACK_SIZE;
    m_stack = new char[m_stack_size];
}

concurrent_$_cls_Coroutine::~concurrent_$_cls_Coroutine()
{
    delete[] m_stack;
}

int concurrent_$_cls_Coroutine::get_ret()
{
    return m_ret;
}

bool concurrent_$_cls_Coroutine::finished()
{
    return m_finished;
}

ucontext_t *concurrent_$_cls_Coroutine::get_ctx()
{
    return &m_ctx;
}

int concurrent_$_cls_Coroutine::method_start()
{
    m_ret = 0;
    m_finished = false;

    if (getcontext(&m_ctx) == -1)
    {
        return -1;
    }
    m_ctx.uc_stack.ss_sp = m_stack;
    m_ctx.uc_stack.ss_size = m_stack_size;
    m_ctx.uc_link = get_coc_sched_ctx();
    makecontext(&m_ctx, co_entry, 0);

    register_coc_co(this);

    return 0;
}

int concurrent_$_cls_Coroutine::method_run()
{
    return 0;
}

void concurrent_$_cls_Coroutine::co_entry()
{
    concurrent_$_cls_Coroutine *co = get_curr_coc_co();
    co->m_ret = co->method_run();
    co->m_finished = true;
}
