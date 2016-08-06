#include "sched.coc.h"
#include "socket.coc_native_mod.h"

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

CocPtr<socket_$_cls_TcpSocket> socket_$_cls_TcpSocket::method_accept()
{
    while (true)
    {
        int fd = accept4(m_sock_fd, NULL, NULL, SOCK_NONBLOCK);
        if (fd != -1)
        {
            return new socket_$_cls_TcpSocket(fd);
        }
        if (errno != EAGAIN)
        {
            return NULL;
        }
        switch_to_sched();
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

int socket_$_cls_TcpSocket::method_send_all(__builtins_$_cls_String *s)
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
            return NULL;
        }
        switch_to_sched();
    }

    return 0;
}

CocPtr<__builtins_$_cls_String> socket_$_cls_TcpSocket::method_recv(coc_uint_t sz)
{
    char *buf = new char[sz];
    while (true)
    {
        ssize_t recv_len = recv(m_sock_fd, buf, sz, 0);
        if (recv_len >= 0)
        {
            CocPtr<__builtins_$_cls_String> ret_str = create_coc_string_from_buf(buf, recv_len);
            delete[] buf;
            return ret_str;
        }
        if (errno != EAGAIN)
        {
            return NULL;
        }
        switch_to_sched();
    }
}

socket_$_cls_TcpSocket::socket_$_cls_TcpSocket(int sock) : m_sock_fd(sock)
{
}

CocPtr<socket_$_cls_TcpSocket> socket_$_func_create_tcp_listen_sock(__builtins_$_cls_String *host, coc_ushort_t port, coc_int_t back_log)
{
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1)
    {
        return NULL;
    }

    int flags = 1;
    if (ioctl(fd, FIONBIO, &flags) == -1)
    {
        close(fd);
        return NULL;
    }

    int reuse_addr = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse_addr, sizeof(reuse_addr)) == -1)
    {
        close(fd);
        return NULL;
    }

    if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == -1)
    {
        close(fd);
        return NULL;
    }

    if (listen(fd, back_log) == -1)
    {
        close(fd);
        return NULL;
    }

    return new socket_$_cls_TcpSocket(fd);
}
