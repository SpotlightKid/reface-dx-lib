# refacedx/constants.py

from rtmidi.midiconstants import END_OF_EXCLUSIVE, SYSTEM_EXCLUSIVE

YAMAHA_MANUFACTURER_ID = 0x43
REFACE_DX_MODEL_ID = 0x05

DUMP_REQUEST = bytes([
    SYSTEM_EXCLUSIVE,
    YAMAHA_MANUFACTURER_ID,
    0x20,   # Device number 0x2n
    0x7F,   # Group number high
    0x1C,   # Group number low
    REFACE_DX_MODEL_ID,
    0,      # Address high
    0,      # Address mid
    0,      # Address low
    END_OF_EXCLUSIVE
])

PARAMETER_CHANGE = bytes([
    SYSTEM_EXCLUSIVE,
    YAMAHA_MANUFACTURER_ID,
    0x10,   # Device number 0x1n
    0x7F,   # Group number high
    0x1C,   # Group number low
    REFACE_DX_MODEL_ID,
    0,      # Address high
    0,      # Address mid
    0,      # Address low
    END_OF_EXCLUSIVE
])

ADDRESS_SYSTEM = (0, 0, 0)
ADDRESS_HEADER = (0x0E, 0x0F, 0)
ADDRESS_VOICE_COMMON = (0x30, 0, 0)
ADDRESS_OPERATOR_1 = (0x31, 0, 0)
ADDRESS_OPERATOR_2 = (0x31, 1, 0)
ADDRESS_OPERATOR_3 = (0x31, 2, 0)
ADDRESS_OPERATOR_4 = (0x31, 3, 0)
ADDRESS_FOOTER = (0x0F, 0x0F, 0)

ADDRESSES_VOICE_BLOCK = (
    ADDRESS_HEADER,
    ADDRESS_VOICE_COMMON,
    ADDRESS_OPERATOR_1,
    ADDRESS_OPERATOR_2,
    ADDRESS_OPERATOR_3,
    ADDRESS_OPERATOR_4,
    ADDRESS_FOOTER
)

PATCH_NAME_LENGTH = 10             # 0x0A
PATCH_NAME_OFFSET = 24             # 0x18
VOICE_COMMON_CHECKSUM_OFFSET = 62  # 0x3E
VOICE_COMMON_DATA_LENGTH = 42      # 0x2A
VOICE_COMMON_DATA_OFFSET = 20      # 0x14
