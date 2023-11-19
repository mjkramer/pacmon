#!/usr/bin/env python3

from collections import defaultdict
from dataclasses import dataclass
import os
from typing import Dict
import time

from construct import Container
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import zmq

from format import Msg, WordType # , WordType_t
from format import PACKET_TYPE_MAP
from util import parity64, get_data_socket


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

        self.influx_org = 'lbl-neutrino'
        self.influx_bucket = 'pacman'
        self.influx_client = InfluxDBClient(url='http://localhost:18086',
                                            token=os.environ['INFLUXDB_TOKEN'],
                                            org=self.influx_org)

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
            else:
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

    def write_to_influx(self, tile_id = 0):
        api = self.influx_client.write_api(write_options=SYNCHRONOUS)

        point = Point('word_types')
        point.tag('tile_id', tile_id)
        for word_type, count in self.word_types.items():
            point.field(word_type, count)
        api.write(bucket=self.influx_bucket, org=self.influx_org, record=point)

        for chan, counts in self.data_statuses.items():
            point = Point('data_statuses')
            point.tag('tile_id', tile_id)
            point.tag('io_channel', chan)
            for field, value in counts.__dict__.items():
                point.field(field, value)
            api.write(bucket=self.influx_bucket, org=self.influx_org, record=point)

        for chan, counts in self.config_statuses.items():
            point = Point('config_statuses')
            point.tag('tile_id', tile_id)
            point.tag('io_channel', chan)
            for field, value in counts.__dict__.items():
                point.field(field, value)
            api.write(bucket=self.influx_bucket, org=self.influx_org, record=point)

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
                    # self.print_stats()
                    self.write_to_influx()
                    last = time.time()


if __name__ == '__main__':
    pacmon = Pacmon()
    pacmon.run()
