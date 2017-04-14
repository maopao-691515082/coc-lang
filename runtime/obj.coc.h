#ifndef OBJ_COC_H
#define OBJ_COC_H

//本文件统一包含在util.coc.h，就不做自包含了

class CocObj
{
protected:
    CocObj() : m_ref_count(0)
    {
    }

    virtual ~CocObj() = 0;

private:
    coc_ulong_t m_ref_count;

    template <typename T>
    friend class CocPtr;
};

template <typename T>
class CocPtr
{
public:
    COC_INLINE CocPtr() : m_ptr(NULL)
    {
    }

    COC_INLINE CocPtr(T *ptr)
    {
        inc_ref_count(ptr);
        m_ptr = ptr;
    }

    COC_INLINE CocPtr(const CocPtr<T> &other)
    {
        other.inc_ref_count();
        m_ptr = other.m_ptr;
    }

    COC_INLINE ~CocPtr()
    {
        dec_ref_count();
    }

    COC_INLINE CocPtr &operator=(T *ptr)
    {
        inc_ref_count(ptr);
        dec_ref_count();
        m_ptr = ptr;
        return *this;
    }

    COC_INLINE CocPtr &operator=(const CocPtr<T> &other)
    {
        other.inc_ref_count();
        dec_ref_count();
        m_ptr = other.m_ptr;
        return *this;
    }

    COC_INLINE T *operator->() const
    {
        return m_ptr;
    }

    COC_INLINE T &operator*() const
    {
        return *m_ptr;
    }

    COC_INLINE operator T *() const
    {
        return m_ptr;
    }

    COC_INLINE CocPtr<T> copy_ptr()
    {
        return m_ptr;
    }

private:
    T *m_ptr;

    static COC_INLINE void inc_ref_count(T *ptr)
    {
        if (ptr != NULL)
        {
            ++ (static_cast<CocObj *>(ptr))->m_ref_count;
        }
    }

    COC_INLINE void inc_ref_count() const
    {
        inc_ref_count(m_ptr);
    }

    static COC_INLINE void dec_ref_count(T *ptr)
    {
        if (ptr != NULL)
        {
            -- (static_cast<CocObj *>(ptr))->m_ref_count;
            if ((static_cast<CocObj *>(ptr))->m_ref_count == 0)
            {
                delete static_cast<CocObj *>(ptr);
            }
        }
    }

    COC_INLINE void dec_ref_count() const
    {
        dec_ref_count(m_ptr);
    }
};

template <typename T>
COC_INLINE CocPtr<T> make_coc_ptr(T *ptr)
{
    return ptr;
}

static COC_INLINE coc_bool_t is_same_coc_obj(CocObj *a, CocObj *b)
{
    return a == b;
}

//从裸指针类型转CocPtr类型，若不是裸指针则保持不变
template <typename T>
struct RawPtrToCocPtr
{
    typedef T Tp;
};
template <typename T>
struct RawPtrToCocPtr<T *>
{
    typedef CocPtr<T> Tp;
};

//从CocPtr类型转裸指针类型，若不是CocPtr则保持不变
template <typename T>
struct CocPtrToRawPtr
{
    typedef T Tp;
};
template <typename T>
struct CocPtrToRawPtr<CocPtr<T> >
{
    typedef T *Tp;
};

#endif
