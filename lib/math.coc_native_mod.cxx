#include "math.coc_native_mod.h"

static void math_$_init_native_global_var()
{
}

coc_double_t math_$_func_fmod(coc_double_t a, coc_double_t b)
{
    return fmod(a, b);
}
