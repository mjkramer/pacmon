#!/usr/bin/env python3

from construct import (
    Array, Byte, Bytes, Enum, Int16ul, Int32ul, Padding, Struct, Switch, this
)

Data = Struct(
    'io_channel' / Byte,
    'timestamp' / Int32ul,
    Padding(2),
    'packet' / Bytes(8)
)

Trig = Struct(
    'type' / Byte,
    Padding(2),
    'timestamp' / Int32ul
)

Sync = Struct(
    'type' / Byte,
    'clk_source' / Byte,
    'timestamp' / Int32ul
)

Ping = Struct(
    Padding(15)
)

Write = Struct(
    Padding(3),
    'write1' / Int32ul,
    Padding(4),
    'write2' / Int32ul
)

Read = Struct(
    Padding(3),
    'read1' / Int32ul,
    Padding(4),
    'read2' / Int32ul
)

Error = Struct(
    'err' / Byte,
    Padding(14)                 # string?
)

WordType = Enum(Byte,
    Data = ord('D'),
    Trig = ord('T'),
    Sync = ord('S'),
    Ping = ord('P'),
    Write = ord('W'),
    Read = ord('R'),
    Error = ord('E')
)

Word = Struct(
    'type' / WordType,
    'content' / Switch(this.type,
        {
            WordType.Data: Data,
            WordType.Trig: Trig,
            WordType.Sync: Sync,
            WordType.Ping: Ping,
            WordType.Write: Write,
            WordType.Read: Read,
            WordType.Error: Error,
        }
    )
)

MsgType = Enum(Byte,
    Data = ord('D'),
    Request = ord('?'),
    Reply = ord('!')
)

Message = Struct(
    'type' / MsgType,
    'timestamp' / Int32ul,
    Padding(1),
    'num_words' / Int16ul,
    'words' / Array(this.num_words, Word)
)

def test_parse():
    import io
    stream = b'D\x00\x00\x04\xd2\x00\x00\x00'
    stream = io.BytesIO(stream)
    Message.parse_stream(stream)
    Message.parse_stream(stream)
    bs = b'D\x00\x00\x04\xd2\x00\x00\x01D\x03\x00\x00\x04\xf2\x00\x00\x12\x23\x34\x45\x54\x43\x32\x21'

def test_build():
    Message.build({'type': MsgType.Data,
                   'timestamp': 1234,
                   'num_words': 0,
                   'words': []})
    w = {'type': WordType.Data,
         'content': {'io_channel': 3,
                     'timestamp': 4321,
                     'packet': 666666}}
    Message.build({'type': MsgType.Data,
                   'timestamp': 1234,
                   'num_words': 1,
                   'words': [w]})
