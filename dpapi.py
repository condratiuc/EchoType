"""Windows DPAPI encryption via ctypes.

Encrypts/decrypts strings using CryptProtectData / CryptUnprotectData,
which ties the ciphertext to the current Windows user account.

Named dpapi.py (not crypto.py) to avoid PyInstaller conflicts with
excluded Crypto / cryptography packages.
"""

import base64
import ctypes
import ctypes.wintypes


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ('cbData', ctypes.wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_char)),
    ]


_crypt32 = ctypes.windll.crypt32
_kernel32 = ctypes.windll.kernel32

_CryptProtectData = _crypt32.CryptProtectData
_CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),  # pDataIn
    ctypes.c_wchar_p,           # szDataDescr
    ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
    ctypes.c_void_p,            # pvReserved
    ctypes.c_void_p,            # pPromptStruct
    ctypes.wintypes.DWORD,      # dwFlags
    ctypes.POINTER(DATA_BLOB),  # pDataOut
]
_CryptProtectData.restype = ctypes.wintypes.BOOL

_CryptUnprotectData = _crypt32.CryptUnprotectData
_CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),  # pDataIn
    ctypes.POINTER(ctypes.c_wchar_p),  # ppszDataDescr
    ctypes.POINTER(DATA_BLOB),  # pOptionalEntropy
    ctypes.c_void_p,            # pvReserved
    ctypes.c_void_p,            # pPromptStruct
    ctypes.wintypes.DWORD,      # dwFlags
    ctypes.POINTER(DATA_BLOB),  # pDataOut
]
_CryptUnprotectData.restype = ctypes.wintypes.BOOL

_LocalFree = _kernel32.LocalFree
_LocalFree.argtypes = [ctypes.c_void_p]
_LocalFree.restype = ctypes.c_void_p


def encrypt_string(plaintext):
    """Encrypt a string using DPAPI. Returns a base64-encoded ciphertext."""
    data = plaintext.encode('utf-8')
    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()

    if not _CryptProtectData(
        ctypes.byref(blob_in), 'EchoType', None, None, None, 0, ctypes.byref(blob_out)
    ):
        raise OSError('CryptProtectData failed')

    try:
        encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return base64.b64encode(encrypted).decode('ascii')
    finally:
        _LocalFree(blob_out.pbData)


def decrypt_string(b64_ciphertext):
    """Decrypt a base64-encoded DPAPI ciphertext back to plaintext string."""
    data = base64.b64decode(b64_ciphertext)
    blob_in = DATA_BLOB(len(data), ctypes.create_string_buffer(data, len(data)))
    blob_out = DATA_BLOB()

    if not _CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    ):
        raise OSError('CryptUnprotectData failed')

    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode('utf-8')
    finally:
        _LocalFree(blob_out.pbData)
