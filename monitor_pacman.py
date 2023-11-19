#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict
import time

from construct import Container
import zmq

from format import Msg, WordType # , WordType_t
from format import PACKET_TYPE_MAP
from util import parity64


def get_data_socket() -> zmq.Socket:
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket_opts = [
        (zmq.LINGER, 1000),
        (zmq.RCVTIMEO, 1000*11),
        (zmq.SNDTIMEO, 1000*11)
    ]
    for opt in socket_opts:
        socket.setsockopt(*opt)
    socket.connect('tcp://pacman32.local:5556')
    socket.setsockopt(zmq.SUBSCRIBE, b'')
    return socket


def get_data_poller() -> zmq.Poller:
    socket = get_data_socket()
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    return poller


def dump_messages(pretty=False):
    poller = get_data_poller()
    while True:
        for socket, _ in poller.poll():
            raw = socket.recv()
            msg = Msg.parse(raw)
            if pretty:
                print(msg)
            else:
                print(raw.hex(sep=' '))


@dataclass
class DataCountsPerStatus:
    total: int = 0
    valid_parity: int = 0
    invalid_parity: int = 0
    downstream: int = 0
    upstream: int = 0


@dataclass
class ConfigCountsPerStatus:
    total: int = 0
    invalid_parity: int = 0
    ds_read: int = 0
    ds_write: int = 0
    us_read: int = 0
    us_write: int = 0


def DataCountsPerStatusPerIOChan() -> Dict[int, DataCountsPerStatus]:
    return defaultdict(lambda: DataCountsPerStatus())

def ConfigCountsPerStatusPerIOChan() -> Dict[int, ConfigCountsPerStatus]:
    return defaultdict(lambda: ConfigCountsPerStatus())

# def CountsPerType() -> Dict[WordType_t, int]:
def CountsPerType() -> Dict[str, int]:
    return defaultdict(lambda: 0)


class Pacmon:
    def __init__(self):
        self.word_types = CountsPerType()
        self.data_statuses = DataCountsPerStatusPerIOChan()
        self.config_statuses = ConfigCountsPerStatusPerIOChan()

        self.data_socket = get_data_socket()

        self.poller = zmq.Poller()
        self.poller.register(self.data_socket, zmq.POLLIN)

    def record_type(self, word: Container):
        # Reclassify Data words according to the LArPix packet type
        if word.type is WordType.Data:
            packet_type = word.content.packet[0] & 3
            # Data, Write, Read, Error
            word_type_reclass = PACKET_TYPE_MAP[packet_type]
        else:
            word_type_reclass = word.type
        self.word_types[word_type_reclass] += 1

    def record_statuses(self, word: Container):
        if word.type is WordType.Data:
            chan = word.content.io_channel
            valid_parity = parity64(word.content.packet)
            downstream = word.content.packet[7] & 0x40 == 0x40

            packet_type = word.content.packet[0] & 3
            is_config_read = PACKET_TYPE_MAP[packet_type] == WordType.Read
            is_config_write = PACKET_TYPE_MAP[packet_type] == WordType.Write
            is_config = is_config_read or is_config_write

            data = self.data_statuses[chan]
            config = self.config_statuses[chan]

            data.total += 1
            if is_config:
                config.total += 1

            if valid_parity:
                data.valid_parity += 1
            else:               # invalid parity
                data.invalid_parity += 1
                if is_config:
                    config.invalid_parity += 1

            if downstream:
                data.downstream += 1
                if is_config_read:
                    config.ds_read += 1
                elif is_config_write:
                    config.ds_write += 1
            else:
                data.upstream += 1
                if is_config_read:
                    config.us_read += 1
                elif is_config_write:
                    config.us_write += 1

    def print_stats(self):
        print(self.word_types)
        print(self.data_statuses)
        print(self.config_statuses)
        print()

    def run(self):
        last = time.time()
        while True:
            for socket, _ in self.poller.poll():
                raw = socket.recv()
                msg = Msg.parse(raw)

                for word in msg.words:
                    self.record_type(word)
                    self.record_statuses(word)

                if time.time() - last > 1:
                    self.print_stats()
                    last = time.time()


if __name__ == '__main__':
    # dump_messages()
    pacmon = Pacmon()
    pacmon.run()
