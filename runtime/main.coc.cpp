#include "util.coc.h"
#include "sched.coc.h"

int main(int argc, char *argv[])
{
    coc_assert(sizeof(size_t) <= sizeof(coc_long_t));

    coc_assert(argc > 0);

    CocPtr<CocArray<__builtins_$_cls_String *> > coc_argv = new CocArray<__builtins_$_cls_String *>(argc);
    for (int i = 0; i < argc; ++ i)
    {
        coc_argv->elem_at(i) = create_coc_string_from_cstring(argv[i]);
    }

    return start_coc_prog(coc_argv);
}
