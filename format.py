#!/usr/bin/env python3

from construct import (
    Array, Byte, Bytes, Enum, Int16ul, Int32ul, Padding, Struct, Switch, this
)


# The "Pac" structs are all 15 bytes. Together with a preceding 1-byte WordType
# they form a Word.

PacData = Struct(
    'io_channel' / Byte,
    'timestamp' / Int32ul,
    Padding(2),
    'packet' / Bytes(8)
)

PacTrig = Struct(
    'type' / Byte,
    Padding(2),
    'timestamp' / Int32ul
)

PacSync = Struct(
    'type' / Byte,
    'clk_source' / Byte,
    'timestamp' / Int32ul
)

PacPing = Struct(
    Padding(15)
)

PacWrite = Struct(
    Padding(3),
    'write1' / Int32ul,
    Padding(4),
    'write2' / Int32ul
)

PacRead = Struct(
    Padding(3),
    'read1' / Int32ul,
    Padding(4),
    'read2' / Int32ul
)

PacError = Struct(
    'err' / Byte,
    Padding(14)                 # string?
)


# NOTE: Apparently, Writes, Reads, and Errors are actually (sometimes?)
# transmitted as Data words; the type is determined from the first two bits of
# the LArPix packet using PACKET_TYPE_MAP below.
WordType = Enum(Byte,
    Data = ord('D'),
    Trig = ord('T'),
    Sync = ord('S'),
    Ping = ord('P'),
    Write = ord('W'),
    Read = ord('R'),
    Error = ord('E')
)

PACKET_TYPE_MAP = {
    0: WordType.Data,
    1: WordType.Error,
    2: WordType.Write,
    3: WordType.Read,
}

# HACK: WordType is not a type per-se, so we must call type() with an arbitrary
# member (e.g. Data) of WordType.
WordType_t = type(WordType.Data) # for use in type annotations

Word = Struct(
    'type' / WordType,
    'content' / Switch(this.type,
        {
            WordType.Data: PacData,
            WordType.Trig: PacTrig,
            WordType.Sync: PacSync,
            WordType.Ping: PacPing,
            WordType.Write: PacWrite,
            WordType.Read: PacRead,
            WordType.Error: PacError,
        }
    )
)


MsgType = Enum(Byte,
    Data = ord('D'),
    Request = ord('?'),
    Reply = ord('!')
)

Msg = Struct(
    'type' / MsgType,
    'timestamp' / Int32ul,
    Padding(1),
    'num_words' / Int16ul,
    'words' / Array(this.num_words, Word)
)
