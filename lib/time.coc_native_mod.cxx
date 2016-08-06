#include "time.coc_native_mod.h"

static void time_$_init_native_global_var()
{
}

coc_long_t time_$_func_time_us()
{
    struct timeval now;
    gettimeofday(&now, NULL);
    return (coc_long_t)now.tv_sec * 1000000 + (coc_long_t)now.tv_usec;
}

CocPtr<__builtins_$_cls_String> time_$_func_strftime(__builtins_$_cls_String *fmt, coc_long_t arg_tm)
{
    time_t tm = (time_t)arg_tm;
    struct tm *pstru_tm = localtime(&tm);
    if (pstru_tm == NULL)
    {
        return create_coc_string_from_literal("");
    }

    static char result[1024 * 1024];
    size_t result_len = strftime(result, sizeof(result), fmt->data(), pstru_tm);
    result[result_len] = '\0';

    return create_coc_string_from_cstring(result);
}
