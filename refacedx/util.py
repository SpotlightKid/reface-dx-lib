# -*- coding: utf-8 -*-
#
# refacedx/util.py

import sys

from .constants import (ADDRESSES_VOICE_BLOCK, PATCH_NAME_LENGTH, PATCH_NAME_OFFSET,
                        REFACE_DX_MODEL_ID, SYSTEM_EXCLUSIVE, VOICE_COMMON_CHECKSUM_OFFSET,
                        VOICE_COMMON_DATA_LENGTH, VOICE_COMMON_DATA_OFFSET, YAMAHA_MANUFACTURER_ID)


def checksum(msg, offset=7, length=None):
    if length is None:
        length = len(msg) - 2
    return ((sum(msg[offset:offset+length]) ^ 0x7f) & 0x7f) + 1


def ellip(s, length=50, suffix='[...]'):
    if not s or len(s) <= length:
        return s
    else:
        return s[:length - len(suffix)] + suffix


def get_patch_name(data, encoding='ascii'):
    return data[PATCH_NAME_OFFSET:PATCH_NAME_OFFSET + PATCH_NAME_LENGTH].decode(encoding).rstrip()


def set_patch_name(data, name):
    patch = bytearray(data)
    name = name.ljust(PATCH_NAME_LENGTH).encode('ascii')[:PATCH_NAME_LENGTH]
    patch[PATCH_NAME_OFFSET:PATCH_NAME_OFFSET + PATCH_NAME_LENGTH] = name
    patch[VOICE_COMMON_CHECKSUM_OFFSET] = checksum(patch, offset=VOICE_COMMON_DATA_OFFSET,
                                                   length=VOICE_COMMON_DATA_LENGTH)
    return patch


if sys.platform.startswith('win'):
    import ctypes
    _NAME_DISPLAY = 3

    def get_fullname():
        GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
        size = ctypes.pointer(ctypes.c_ulong(0))
        GetUserNameEx(_NAME_DISPLAY, None, size)
        name_buf = ctypes.create_unicode_buffer(size.contents.value)
        GetUserNameEx(_NAME_DISPLAY, name_buf, size)
        return name_buf.value
else:
    import getpass
    import pwd

    def get_fullname():
        """Get the current user's full name, if possible."""
        username = getpass.getuser()
        return pwd.getpwnam(username).pw_gecos.split(',')[0]


def is_reface_dx_bulk_dump(msg, address=None, device=None):
    if len(msg) <= 12:
        return False

    if not all((
            msg[0] == SYSTEM_EXCLUSIVE,
            msg[1] == YAMAHA_MANUFACTURER_ID,
            msg[3] == 0x7f,
            msg[4] == 0x1C,
            msg[7] == REFACE_DX_MODEL_ID)):
        return False

    if device is not None and msg[2] != (0x20 | device):
        return False

    if address and not tuple(msg[8:11]) == address:
        return False

    return True


def is_reface_dx_voice(data):
    for part, address in zip(split_sysex(data), ADDRESSES_VOICE_BLOCK):
        if not is_reface_dx_bulk_dump(part, address=address):
            return False
    else:
        return True


def split_sysex(data):
    # XXX: quick hack to extract sysex messages from binary data
    return [b'\xF0' + m.split(b'\xF7', 1)[0] + b'\xF7'
            for m in data.split(b'\xF0')[1:]]
