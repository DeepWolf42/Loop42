"""Consumer-owned process containment for registered verification commands.

Windows commands start through this trusted wrapper, which joins the parent's
Job Object before spawning any command. This closes the child-before-assignment
race without relying on private Popen thread handles. POSIX uses a new session.
This is lifetime containment, not a security sandbox.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid


def _windows_api():
    from ctypes import wintypes
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'CreateJobObjectW': ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
        'OpenJobObjectW': ([wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
        'SetInformationJobObject': ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        'QueryInformationJobObject': ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
        'AssignProcessToJobObject': ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
        'TerminateJobObject': ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        'GetCurrentProcess': ([], wintypes.HANDLE),
        'CloseHandle': ([wintypes.HANDLE], wintypes.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(api, name)
        function.argtypes = arguments
        function.restype = result
    return api


def _checked(value):
    if not value:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


class VerificationProcess:
    def __init__(self, argv: tuple[str, ...], workspace: Path):
        self.job = None
        self.process = None
        if os.name == 'nt':
            self.api = _windows_api()
            name = 'Local\\Loop42Verification-' + uuid.uuid4().hex
            self.job = _checked(self.api.CreateJobObjectW(None, name))
            try:
                # JOBOBJECT_EXTENDED_LIMIT_INFORMATION, 144 bytes on 64-bit
                # Windows, 112 on 32-bit; LimitFlags is at byte offset 16.
                size = 144 if ctypes.sizeof(ctypes.c_void_p) == 8 else 112
                limits = ctypes.create_string_buffer(size)
                ctypes.c_uint32.from_buffer(limits, 16).value = 0x2000  # KILL_ON_JOB_CLOSE
                _checked(self.api.SetInformationJobObject(self.job, 9, limits, size))
                self.process = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), name, json.dumps(argv)],
                    cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, shell=False,
                )
            except BaseException:
                self.api.CloseHandle(self.job)
                self.job = None
                raise
        else:
            self.process = subprocess.Popen(argv, cwd=workspace, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, start_new_session=True)

    def terminate(self):
        if self.job is not None:
            # Stop the trusted wrapper even if it has not joined the Job yet.
            # Waiting first prevents a late assignment after the empty check.
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait(timeout=3)
            _checked(self.api.TerminateJobObject(self.job, 1))
            deadline = time.monotonic() + 3
            accounting = ctypes.create_string_buffer(48)
            while True:
                _checked(self.api.QueryInformationJobObject(self.job, 1, accounting, 48, None))
                if ctypes.c_uint32.from_buffer(accounting, 40).value == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError('verification process tree did not become quiescent')
                time.sleep(0.01)
        else:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.process.wait(timeout=3)

    def close(self):
        if self.job is not None:
            self.api.CloseHandle(self.job)
            self.job = None


def _main() -> int:
    api = _windows_api()
    job = _checked(api.OpenJobObjectW(0x0001, False, sys.argv[1]))  # ASSIGN_PROCESS
    try:
        _checked(api.AssignProcessToJobObject(job, api.GetCurrentProcess()))
        return subprocess.call(json.loads(sys.argv[2]), stdin=subprocess.DEVNULL, shell=False)
    finally:
        api.CloseHandle(job)


if __name__ == '__main__':
    raise SystemExit(_main())
