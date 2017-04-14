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

    ElemType method_get(coc_long_t idx)
    {
        coc_assert(idx >= 0 && (coc_ulong_t)idx < m_vec.size());
        return m_vec[(size_t)idx];
    }

    void method_set(coc_long_t idx, ElemRawType elem)
    {
        coc_assert(idx >= 0 && (coc_ulong_t)idx < m_vec.size());
        m_vec[(size_t)idx] = elem;
    }

private:
    ~util_$_cls_Vector()
    {
    }

    std::vector<ElemType> m_vec;
};

#endif
