#ifndef ARRAY_COC_H
#define ARRAY_COC_H

//本文件统一包含在util.coc.h，就不做自包含了

template <typename T>
class CocArray;

//虽然有其他办法（如CocPtr里面弄个typedef T XXX）也能解决推导的问题，不过用偏特化实现最严谨的检查
template <typename T>
struct AssertCocPtrOfCocArray
{
};
template <typename T>
struct AssertCocPtrOfCocArray<CocPtr<CocArray<T> > >
{
    typedef T ElemType;
};

template <typename T>
class CocArray : public CocObj
{
public:
    typedef typename RawPtrToCocPtr<T>::Tp ElemType;
    typedef typename CocPtrToRawPtr<ElemType>::Tp ElemRawType;

    template <typename T_sz>
    CocArray(T_sz sz)
    {
        m_size = sz;
        coc_assert(m_size >= 0);
        m_array = new ElemType[m_size];
        for (coc_long_t i = 0; i < m_size; ++ i)
        {
            m_array[i] = ElemType();
        }
    }

    template <typename T_sz, typename ...Args>
    CocArray(T_sz sz, Args ...sz_list_left)
    {
        m_size = sz;
        coc_assert(m_size >= 0);
        m_array = new ElemType[m_size];
        for (coc_long_t i = 0; i < m_size; ++ i)
        {
            m_array[i] = new CocArray<typename AssertCocPtrOfCocArray<ElemType>::ElemType>(sz_list_left...);
        }
    }

    COC_INLINE coc_long_t size()
    {
        return m_size;
    }

    COC_INLINE ElemType &elem_at(coc_long_t idx)
    {
        if (idx < 0)
        {
            idx += m_size;
        }
        coc_assert(idx >= 0 && idx < m_size);
        return m_array[idx];
    }

private:
    virtual ~CocArray()
    {
        if (m_array != NULL)
        {
            delete[] m_array;
        }
    }

    ElemType *m_array;
    coc_long_t m_size;
};

#endif
