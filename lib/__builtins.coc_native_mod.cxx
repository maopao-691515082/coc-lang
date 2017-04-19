#include "__builtins.coc_native_mod.h"

static void __builtins_$_init_native_global_var()
{
}

__builtins_$_cls_String::~__builtins_$_cls_String()
{
    delete[] m_data;
}

coc_long_t __builtins_$_cls_String::method_size()
{
    return m_sz;
}

coc_char_t __builtins_$_cls_String::method_char_at(coc_long_t idx)
{
    coc_assert(idx >= 0 && idx < m_sz);
    return m_data[idx];
}

coc_int_t __builtins_$_cls_String::method_cmp(__builtins_$_cls_String *other)
{
    int rc = memcmp(m_data, other->m_data, (size_t)(m_sz < other->m_sz ? m_sz : other->m_sz));
    if (rc < 0)
    {
        return -1;
    }
    if (rc > 0)
    {
        return 1;
    }
    if (m_sz < other->m_sz)
    {
        return -1;
    }
    if (m_sz > other->m_sz)
    {
        return 1;
    }
    return 0;
}

CocPtr<__builtins_$_cls_String> __builtins_$_cls_String::method_concat(__builtins_$_cls_String *other)
{
    coc_long_t sz = m_sz + other->m_sz;
    coc_char_t *new_data = new coc_char_t[sz + 1];
    memcpy(new_data, m_data, (size_t)m_sz);
    memcpy(new_data + m_sz, other->m_data, (size_t)other->m_sz);
    new_data[sz] = '\0';

    __builtins_$_cls_String *new_str = new __builtins_$_cls_String();
    new_str->m_data = new_data;
    new_str->m_sz = sz;
    return new_str;
}

const coc_char_t *__builtins_$_cls_String::data()
{
    return m_data;
}

__builtins_$_cls_String::__builtins_$_cls_String()
{
}

__builtins_$_cls_String::__builtins_$_cls_String(const char *s)
{
    _init(s, (coc_long_t)strlen(s));
}

__builtins_$_cls_String::__builtins_$_cls_String(const char *buf, coc_long_t sz)
{
    _init(buf, sz);
}

void __builtins_$_cls_String::_init(const char *buf, coc_long_t sz)
{
    coc_assert(sz >= 0);
    m_data = new coc_char_t[sz + 1];
    memcpy(m_data, buf, (size_t)sz);
    m_data[sz] = '\0';
    m_sz = sz;
}

CocPtr<__builtins_$_cls_String> create_coc_string_from_cstring(const char *s)
{
    return new __builtins_$_cls_String(s);
}

CocPtr<__builtins_$_cls_String> create_coc_string_from_format(const char *fmt, ...)
{
    static char static_buf[4096];
    char *buf = static_buf;
    size_t buf_len = strlen(fmt) * 2;
    if (buf_len > sizeof(static_buf))
    {
        buf = new char[buf_len];
    }
    else
    {
        buf_len = sizeof(static_buf);
    }

    for (;;)
    {
        buf[buf_len - 2] = '\0';
        va_list ap;
        va_start(ap, fmt);
        vsnprintf(buf, buf_len, fmt, ap);
        va_end(ap);
        if (buf[buf_len - 2] == '\0')
        {
            break;
        }
        if (buf != static_buf)
        {
            delete[] buf;
        }
        buf_len *= 2;
        buf = new char[buf_len];
    }

    __builtins_$_cls_String *str = new __builtins_$_cls_String(buf);

    if (buf != static_buf)
    {
        delete[] buf;
    }

    return str;
}

CocPtr<__builtins_$_cls_String> create_coc_string_from_buf(const char *buf, coc_long_t sz)
{
    return new __builtins_$_cls_String(buf, sz);
}
