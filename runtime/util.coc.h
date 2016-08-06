#ifndef UTIL_COC_H
#define UTIL_COC_H

#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <cstring>
#include <cstdarg>
#include <cmath>
#include <ctime>

#include <vector>
#include <map>
#include <list>

#include <sys/time.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <errno.h>

#define COC_INLINE inline __attribute__((always_inline))

static COC_INLINE void coc_assert(bool cond)
{
    if (!cond)
    {
        abort();
    }
}

typedef void coc_void_t;
typedef bool coc_bool_t;
typedef int8_t coc_byte_t;
typedef uint8_t coc_ubyte_t;
typedef char coc_char_t;
typedef int16_t coc_short_t;
typedef uint16_t coc_ushort_t;
typedef int32_t coc_int_t;
typedef uint32_t coc_uint_t;
typedef int64_t coc_long_t;
typedef uint64_t coc_ulong_t;
typedef float coc_float_t;
typedef double coc_double_t;
typedef long double coc_ldouble_t;

#include "obj.coc.h"
#include "array.coc.h"
#include "op.coc.h"

#include "__builtins.coc_mod.h"

#endif
