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
    Data = ord('D'),
    Trig = ord('T'),
    Sync = ord('S'),
    Ping = ord('P'),
    Write = ord('W'),
    Read = ord('R'),
    Error = ord('E')
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

msgtype = Enum(Byte,
    Data = ord('D'),
    Request = ord('?'),
    Reply = ord('!')
)

message = Struct(
    'type' / msgtype,
    'timestamp' / Int32ub,
    Padding(1),
    'num_words' / Int16ub,
    'words' / Array(this.num_words, word)
)

def test_parse():
    import io
    stream = b'D\x00\x00\x04\xd2\x00\x00\x00D\x00\x00\x04\xf2\x00\x00\x00'
    stream = io.BytesIO(stream)
    m1 = message.parse_stream(stream)
    m2 = message.parse_stream(stream)
    return m1, m2

def test_build():
    message.build({'type': msgtype.Data,
                   'timestamp': 1234,
                   'num_words': 0,
                   'words': []})
    w = {'type': wordtype.Data,
         'content': {'io_channel': 3,
                     'timestamp': 4321,
                     'packet': 666666}}
    message.build({'type': msgtype.Data,
                   'timestamp': 1234,
                   'num_words': 1,
                   'words': [w]})
