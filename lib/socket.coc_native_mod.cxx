#include "sched.coc.h"
#include "socket.coc_native_mod.h"

class SocketErrorImpl : public socket_$_cls_SocketError
{
public:
    SocketErrorImpl(__builtins_$_cls_String *msg);

    virtual CocPtr<__builtins_$_cls_String> method_err_msg();

private:

    CocPtr<__builtins_$_cls_String> m_err_msg;
};

SocketErrorImpl::SocketErrorImpl(__builtins_$_cls_String *msg) : m_err_msg(msg)
{
}

CocPtr<__builtins_$_cls_String> SocketErrorImpl::method_err_msg()
{
    return m_err_msg;
}

static void socket_$_init_native_global_var()
{
}

socket_$_cls_TcpSocket::~socket_$_cls_TcpSocket()
{
    if (m_sock_fd >= 0)
    {
        close(m_sock_fd);
    }
}

CocPtr<socket_$_cls_SocketError> socket_$_cls_TcpSocket::method_accept(CocPtr<socket_$_cls_TcpSocket> &conn_sock)
{
    conn_sock = NULL;

    while (true)
    {
        int fd = accept4(m_sock_fd, NULL, NULL, SOCK_NONBLOCK);
        if (fd != -1)
        {
            conn_sock = new socket_$_cls_TcpSocket(fd);
            return NULL;
        }
        if (errno != EAGAIN)
        {
            return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("accept failed, errno[%d]", errno)));
        }
        switch_to_coc_sched_co();
    }
}

CocPtr<__builtins_$_cls_String> socket_$_cls_TcpSocket::method_get_peer_name()
{
    struct sockaddr_in addr;
    socklen_t addr_len = sizeof(addr);
    if (getpeername(m_sock_fd, (struct sockaddr *)&addr, &addr_len) == -1)
    {
        return create_coc_string_from_literal("");
    }
    return create_coc_string_from_format("%s:%u", inet_ntoa(addr.sin_addr), (unsigned int)ntohs(addr.sin_port));
}

CocPtr<socket_$_cls_SocketError> socket_$_cls_TcpSocket::method_send_all(__builtins_$_cls_String *s)
{
    const coc_char_t *buf = s->data();
    coc_long_t sz = s->method_size();

    while (sz > 0)
    {
        ssize_t send_len = send(m_sock_fd, buf, sz, 0);
        if (send_len >= 0)
        {
            buf += send_len;
            sz -= send_len;
            continue;
        }
        if (errno != EAGAIN)
        {
            return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("send failed, errno[%d]", errno)));
        }
        switch_to_coc_sched_co();
    }

    return NULL;
}

CocPtr<socket_$_cls_SocketError> socket_$_cls_TcpSocket::method_recv(coc_uint_t sz, CocPtr<__builtins_$_cls_String> &s)
{
    s = NULL;

    char *buf = new char[sz];
    while (true)
    {
        ssize_t recv_len = recv(m_sock_fd, buf, sz, 0);
        if (recv_len >= 0)
        {
            s = create_coc_string_from_buf(buf, recv_len);
            delete[] buf;
            return NULL;
        }
        if (errno != EAGAIN)
        {
            return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("recv failed, errno[%d]", errno)));
        }
        switch_to_coc_sched_co();
    }
}

socket_$_cls_TcpSocket::socket_$_cls_TcpSocket(int sock) : m_sock_fd(sock)
{
}

CocPtr<socket_$_cls_SocketError> socket_$_func_create_tcp_listen_sock(
    __builtins_$_cls_String *host, coc_ushort_t port, coc_int_t back_log, CocPtr<socket_$_cls_TcpSocket> &listen_sock)
{
    listen_sock = NULL;

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
    {
        return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("create socket failed, errno[%d]", errno)));
    }

    int saved_errno = 0;

    int flags = 1;
    if (ioctl(fd, FIONBIO, &flags) == -1)
    {
        saved_errno = errno;
        close(fd);
        return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("set nonblock failed, errno[%d]", saved_errno)));
    }

    int reuse_addr = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse_addr, sizeof(reuse_addr)) == -1)
    {
        saved_errno = errno;
        close(fd);
        return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("set reuseaddr failed, errno[%d]", saved_errno)));
    }

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1)
    {
        saved_errno = errno;
        close(fd);
        return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("bind failed, errno[%d]", saved_errno)));
    }

    if (listen(fd, back_log) == -1)
    {
        saved_errno = errno;
        close(fd);
        return (socket_$_cls_SocketError *)(new SocketErrorImpl(create_coc_string_from_format("listen failed, errno[%d]", saved_errno)));
    }

    listen_sock = new socket_$_cls_TcpSocket(fd);
    return NULL;
}
