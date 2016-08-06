#ifndef SOCKET_COC_NATIVE_MOD_H
#define SOCKET_COC_NATIVE_MOD_H

#include "util.coc.h"

class socket_$_cls_TcpSocket : public CocObj
{
public:
    CocPtr<socket_$_cls_TcpSocket> method_accept();
    CocPtr<__builtins_$_cls_String> method_get_peer_name();
    int method_send_all(__builtins_$_cls_String *s);
    CocPtr<__builtins_$_cls_String> method_recv(coc_uint_t sz);

private:
    virtual ~socket_$_cls_TcpSocket();
    socket_$_cls_TcpSocket(int sock);

    int m_sock_fd;

    friend CocPtr<socket_$_cls_TcpSocket> socket_$_func_create_tcp_listen_sock(__builtins_$_cls_String *host, coc_ushort_t port,
                                                                               coc_int_t back_log);
};

CocPtr<socket_$_cls_TcpSocket> socket_$_func_create_tcp_listen_sock(__builtins_$_cls_String *host, coc_ushort_t port, coc_int_t back_log);

#endif
