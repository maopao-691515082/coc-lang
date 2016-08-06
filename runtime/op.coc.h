#ifndef OP_COC_H
#define OP_COC_H

//本文件统一包含在util.coc.h，就不做自包含了

template <typename T>
void inc_coc_obj(T &num)
{
    ++ num;
}
template <typename T>
void inc_coc_obj(CocPtr<T> &coc_ptr)
{
    coc_ptr.method___op_inc();
}

#endif
