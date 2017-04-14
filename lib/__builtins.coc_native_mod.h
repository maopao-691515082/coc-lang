#ifndef __BUILTINS_COC_NATIVE_MOD_H
#define __BUILTINS_COC_NATIVE_MOD_H

#include "util.coc.h"

#define __builtins_$_func_assert(_cond) (coc_assert(_cond))

class __builtins_$_cls_String : public CocObj
{
public:
    coc_long_t method_size();

    coc_char_t method_char_at(coc_long_t idx);
    coc_int_t method_cmp(__builtins_$_cls_String *other);
    CocPtr<__builtins_$_cls_String> method_concat(__builtins_$_cls_String *other);

    const coc_char_t *data();

private:
    virtual ~__builtins_$_cls_String();
    __builtins_$_cls_String();
    __builtins_$_cls_String(const char *s);
    __builtins_$_cls_String(const char *buf, coc_long_t sz);
    void _init(const char *data, coc_long_t sz);

    coc_char_t *m_data;
    coc_long_t m_sz;

    template <size_t sz>
    friend CocPtr<__builtins_$_cls_String> create_coc_string_from_literal(const char (&s)[sz]);
    friend CocPtr<__builtins_$_cls_String> create_coc_string_from_cstring(const char *s);
    friend CocPtr<__builtins_$_cls_String> create_coc_string_from_format(const char *fmt, ...);
    friend CocPtr<__builtins_$_cls_String> create_coc_string_from_buf(const char *buf, coc_long_t sz);
};

template <size_t sz>
CocPtr<__builtins_$_cls_String> create_coc_string_from_literal(const char (&s)[sz])
{
    coc_assert(sz > 0);
    return new __builtins_$_cls_String(s, (coc_long_t)(sz - 1));
}
CocPtr<__builtins_$_cls_String> create_coc_string_from_cstring(const char *s);
CocPtr<__builtins_$_cls_String> create_coc_string_from_format(const char *fmt, ...);
CocPtr<__builtins_$_cls_String> create_coc_string_from_buf(const char *buf, coc_long_t sz);

#endif
