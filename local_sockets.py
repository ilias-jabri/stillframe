"""Use Linux seccomp to allow only Unix-domain sockets."""

import ctypes
import errno
import os
import socket


class ArgumentComparison(ctypes.Structure):
    _fields_ = [("index", ctypes.c_uint), ("operation", ctypes.c_int),
                ("value", ctypes.c_uint64), ("other", ctypes.c_uint64)]


def require_local_sockets():
    seccomp = ctypes.CDLL("libseccomp.so.2")
    seccomp.seccomp_init.argtypes = (ctypes.c_uint32,)
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = (ctypes.c_char_p,)
    seccomp.seccomp_rule_add_array.argtypes = (
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint,
        ctypes.POINTER(ArgumentComparison),
    )
    seccomp.seccomp_load.argtypes = (ctypes.c_void_p,)
    seccomp.seccomp_release.argtypes = (ctypes.c_void_p,)
    seccomp.seccomp_release.restype = None

    allow = 0x7fff0000
    reject = 0x00050000 | errno.EPERM
    not_equal = 1
    context = seccomp.seccomp_init(allow)
    if not context:
        raise OSError("Could not initialize the socket filter.")

    def check(result):
        if result < 0:
            raise OSError(-result, os.strerror(-result))

    try:
        family = ArgumentComparison(0, not_equal, socket.AF_UNIX, 0)
        for call in (b"socket", b"socketpair"):
            syscall = seccomp.seccomp_syscall_resolve_name(call)
            check(seccomp.seccomp_rule_add_array(context, reject, syscall, 1,
                                                 ctypes.byref(family)))
        check(seccomp.seccomp_load(context))
    finally:
        seccomp.seccomp_release(context)
