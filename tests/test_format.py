#!/usr/bin/env python3

import io

from format import Msg, MsgType, WordType


def test_parse():
    stream = b'D\x00\x00\x04\xd2\x00\x00\x00'
    stream = io.BytesIO(stream)
    Msg.parse_stream(stream)
    Msg.parse_stream(stream)
    bs = b'D\x00\x00\x04\xd2\x00\x01\x00D\x03\x00\x00\x04\xf2\x00\x00\x12\x23\x34\x45\x54\x43\x32\x21'
    Msg.parse(bs)


def test_build():
    Msg.build({'type': MsgType.Data,
               'timestamp': 1234,
               'num_words': 0,
               'words': []})
    w = {'type': WordType.Data,
         'content': {'io_channel': 3,
                     'timestamp': 4321,
                     'packet': 666666}}
    Msg.build({'type': MsgType.Data,
               'timestamp': 1234,
               'num_words': 1,
               'words': [w]})
