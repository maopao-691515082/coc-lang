#include "sched.coc.h"
#include "booter.coc.h"

class MainCo : public concurrent_$_cls_Coroutine
{
public:
    MainCo(CocArray<__builtins_$_cls_String *> *coc_argv);

private:
    virtual int method_run();

    CocArray<__builtins_$_cls_String *> *m_coc_argv;
};

MainCo::MainCo(CocArray<__builtins_$_cls_String *> *coc_argv) : m_coc_argv(coc_argv)
{
}

int MainCo::method_run()
{
    init_coc_mod_literal_str();
    init_coc_mod_global_var();
    return coc_main(m_coc_argv);
}

typedef std::list<CocPtr<concurrent_$_cls_Coroutine> > CoList;

static CocPtr<MainCo> g_main_co = NULL;
static CoList g_co_list;
static concurrent_$_cls_Coroutine *g_curr_co = NULL;
static ucontext_t g_sched_ctx;

static void continue_run_co(concurrent_$_cls_Coroutine *co)
{
    g_curr_co = co;
    coc_assert(swapcontext(&g_sched_ctx, g_curr_co->get_ctx()) != -1);
    g_curr_co = NULL;
}

static void dispach()
{
    while (true)
    {
        coc_assert(!g_co_list.empty());
        for (CoList::iterator iter = g_co_list.begin(); iter != g_co_list.end();)
        {
            concurrent_$_cls_Coroutine *co = (*iter);
            continue_run_co(co);
            if (co->finished())
            {
                if (is_same_coc_obj(co, g_main_co))
                {
                    return;
                }
                g_co_list.erase(iter ++);
            }
            else
            {
                ++ iter;
            }
        }
        usleep(1000);
    }
}

int start_coc_prog(CocArray<__builtins_$_cls_String *> *coc_argv)
{
    concurrent_$_init_default_coroutine_stack_size();
    g_main_co = new MainCo(coc_argv);
    if (g_main_co->method_start() != 0)
    {
        g_main_co = NULL;
        return -1;
    }

    dispach();
    int main_ret = g_main_co->get_ret();
    g_main_co = NULL;
    g_co_list.clear();
    return main_ret;
}

ucontext_t *get_coc_sched_ctx()
{
    return &g_sched_ctx;
}

void register_coc_co(concurrent_$_cls_Coroutine *co)
{
    g_co_list.push_back(co);
}

concurrent_$_cls_Coroutine *get_curr_coc_co()
{
    return g_curr_co;
}

void switch_to_coc_sched_co()
{
    coc_assert(g_curr_co != NULL);
    coc_assert(swapcontext(g_curr_co->get_ctx(), &g_sched_ctx) != -1);
}
