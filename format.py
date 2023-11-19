#!/usr/bin/env python3

from construct import *

data = Struct(
    'io_channel' / Byte,
    'timestamp' / Int32ub,
    Padding(2),
    'packet' / Bytes(8)
)

trig = Struct(
    'type' / Byte,
    Padding(2),
    'timestamp' / Int32ub
)

sync = Struct(
    'type' / Byte,
    'clk_source' / Byte,
    'timestamp' / Int32ub
)

ping = Struct(
    Padding(15)
)

write = Struct(
    Padding(3),
    'write1' / Int32ub,
    Padding(4),
    'write2' / Int32ub
)

read = Struct(
    Padding(3),
    'read1' / Int32ub,
    Padding(4),
    'read2' / Int32ub
)

error = Struct(
    'err' / Byte,
    Padding(14)                 # string?
)

wordtype = Enum(Byte,
    Data = b'D',
    Trig = b'T',
    Sync = b'S',
    Ping = b'P',
    Write = b'W',
    Read = b'R',
    Error = b'E'
)

word = Struct(
    'type' / wordtype,
    'content' / Switch(this.type,
        {
            wordtype.Data: data,
            wordtype.Trig: trig,
            wordtype.Sync: sync,
            wordtype.Ping: ping,
            wordtype.Write: write,
            wordtype.Read: read,
            wordtype.Error: error,
        }
    )
)

# FIXME: Byte doesn't seem to work right
msgtype = Enum(Byte,
    Data = b'D',
    Request = b'?',
    Reply = b'!'
)

message = Struct(
    'type' / msgtype,
    'timestamp' / Int32ub,
    Padding(1),
    'num_words' / Int16ub,
    'words' / Array(this.num_words, word)
)

def test():
    import io
    stream = b'D\x00\x00\x04\xd2\x00\x00\x00D\x00\x00\x04\xf2\x00\x00\x00'
    stream = io.BytesIO(stream)
    m1 = message.parse_stream(stream)
    m2 = message.parse_stream(stream)
