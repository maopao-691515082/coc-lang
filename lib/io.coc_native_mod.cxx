#include "io.coc_native_mod.h"

static void io_$_init_native_global_var()
{
}

io_$_cls_File::io_$_cls_File(__builtins_$_cls_String *file_name, __builtins_$_cls_String *mode)
{
    m_fp = fopen(file_name->data(), mode->data());
    m_need_close = true;
}

io_$_cls_File::io_$_cls_File(FILE *fp) : m_fp(fp), m_need_close(false)
{
}

io_$_cls_File::~io_$_cls_File()
{
    if (m_need_close && m_fp != NULL)
    {
        fclose(m_fp);
    }
}

coc_int_t io_$_cls_File::method_write(__builtins_$_cls_String *s)
{
    if (m_fp == NULL)
    {
        return -1;
    }

    const coc_char_t *data = s->data();
    coc_long_t pos = 0;
    coc_long_t left_count = s->method_size();
    while (left_count > 0)
    {
        coc_long_t write_count = fwrite(data + pos, 1, left_count, m_fp);
        if (ferror(m_fp))
        {
            return -2;
        }
        pos += write_count;
        left_count -= write_count;
    }

    return 0;
}

CocPtr<io_$_cls_File> create_file_from_FILE_ptr(FILE *fp)
{
    return new io_$_cls_File(fp);
}
