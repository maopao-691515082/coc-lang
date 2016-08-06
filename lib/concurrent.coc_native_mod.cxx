#include "sched.coc.h"
#include "concurrent.coc_native_mod.h"

static void concurrent_$_init_native_global_var()
{
}

concurrent_$_cls_Coroutine::concurrent_$_cls_Coroutine()
{
}

concurrent_$_cls_Coroutine::~concurrent_$_cls_Coroutine()
{
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
    m_ctx.uc_stack.ss_size = sizeof(m_stack);
    m_ctx.uc_link = get_sched_ctx();
    makecontext(&m_ctx, co_entry, 0);

    register_co(this);

    return 0;
}

void concurrent_$_cls_Coroutine::co_entry()
{
    concurrent_$_cls_Coroutine *co = get_curr_co();
    co->m_ret = co->method_run();
    co->m_finished = true;
}
