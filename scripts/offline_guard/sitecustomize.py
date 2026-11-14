"""Fail closed in offline Python processes, including inherited child interpreters."""

import atexit
import os
import socket
import subprocess
from pathlib import Path

if os.environ.get("ZHIJIAN_OFFLINE_GUARD") == "1":

    def deny(*args, **kwargs):
        audit = os.environ.get("ZHIJIAN_NETWORK_AUDIT")
        if audit:
            with open(audit, "a") as stream:
                stream.write("BLOCKED_NETWORK_OR_EXTERNAL_PROCESS\n")
        raise RuntimeError("Offline gate forbids sockets and non-Python subprocesses")

    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.socket.sendto = deny
    socket.create_connection = deny
    socket.getaddrinfo = deny
    original_popen = subprocess.Popen
    guard = str(Path(__file__).resolve().parent)

    def guarded_popen(args, *positional, **kwargs):
        command = args[0] if isinstance(args, (list, tuple)) else args
        if isinstance(args, (list, tuple)) and tuple(args) in {("uname", "-p"), ("/sbin/mount",)}:
            return original_popen(args, *positional, **kwargs)
        if kwargs.get("shell") or not Path(str(command)).name.startswith("python"):
            return deny()
        env = dict(kwargs.get("env") or os.environ)
        env["PYTHONPATH"] = guard + os.pathsep + env.get("PYTHONPATH", "")
        env["ZHIJIAN_OFFLINE_GUARD"] = "1"
        env["ZHIJIAN_NETWORK_AUDIT"] = os.environ.get("ZHIJIAN_NETWORK_AUDIT", "")
        kwargs["env"] = env
        return original_popen(args, *positional, **kwargs)

    subprocess.Popen = guarded_popen

    def fail_if_attempted():
        audit = os.environ.get("ZHIJIAN_NETWORK_AUDIT")
        if audit and Path(audit).exists() and Path(audit).stat().st_size:
            os._exit(91)  # Even a caught network error must fail the gate.

    atexit.register(fail_if_attempted)
