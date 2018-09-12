# -*- coding: utf-8 -*-
#
# refacedx/util.py

from .constants import (ADDRESSES_VOICE_BLOCK, REFACE_DX_MODEL_ID, SYSTEM_EXCLUSIVE,
                        YAMAHA_MANUFACTURER_ID)


def split_sysex(data):
    # XXX: quick hack to extract sysex messages from binary data
    return [b'\xF0' + m.split(b'\xF7', 1)[0] + b'\xF7'
            for m in data.split(b'\xF0')[1:]]


def checksum(msg, offset=7, length=-2):
    return sum(msg[offset:length]) & 0x7f


def get_patch_name(data, encoding='ascii'):
    return data[24:34].decode(encoding).rstrip()


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
