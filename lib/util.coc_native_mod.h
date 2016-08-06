#ifndef UTIL_COC_NATIVE_MOD_H
#define UTIL_COC_NATIVE_MOD_H

#include "util.coc.h"

template <typename E>
class util_$_cls_Vector : public CocObj
{
public:
    typedef typename RawPtrToCocPtr<E>::Tp ElemType;
    typedef typename CocPtrToRawPtr<ElemType>::Tp ElemRawType;

    util_$_cls_Vector(coc_long_t sz)
    {
        coc_assert(sz >= 0 && (coc_ulong_t)sz < SIZE_MAX);
        m_vec.resize((size_t)sz);
    }

    ElemType method___op_item_get(coc_long_t idx)
    {
        idx = convert_and_check_idx(idx);
        return m_vec[(size_t)idx];
    }

    void method___op_item_set(coc_long_t idx, ElemRawType elem)
    {
        idx = convert_and_check_idx(idx);
        m_vec[(size_t)idx] = elem;
    }

    void method___op_item_inc(coc_long_t idx)
    {
        idx = convert_and_check_idx(idx);
        inc_coc_obj(m_vec[(size_t)idx]);
    }

private:
    ~util_$_cls_Vector()
    {
    }

    COC_INLINE coc_long_t convert_and_check_idx(coc_long_t idx)
    {
        if (idx < 0)
        {
            idx += m_vec.size();
        }
        coc_assert(idx >= 0 && (coc_ulong_t)idx < m_vec.size());
        return idx;
    }

    std::vector<ElemType> m_vec;
};

#endif
