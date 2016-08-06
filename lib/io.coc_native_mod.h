#ifndef IO_COC_NATIVE_MOD_H
#define IO_COC_NATIVE_MOD_H

#include "util.coc.h"

class io_$_cls_File : public CocObj
{
public:
    io_$_cls_File(__builtins_$_cls_String *file_name, __builtins_$_cls_String *mode);

    coc_int_t method_write(__builtins_$_cls_String *s);

private:
    virtual ~io_$_cls_File();
    io_$_cls_File(FILE *fp);

    FILE *m_fp;
    bool m_need_close;

    friend CocPtr<io_$_cls_File> create_file_from_FILE_ptr(FILE *fp);
};

CocPtr<io_$_cls_File> create_file_from_FILE_ptr(FILE *fp);

#endif
