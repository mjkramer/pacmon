#!/usr/bin/env python3

import zmq

from format import Msg

def parity64(data: bytes) -> int:
    x = ((data[0] << 56) | (data[1] << 48) | (data[2] << 40) | (data[3] << 32) |
         (data[4] << 24) | (data[5] << 16) | (data[6] << 8)  | (data[7]))
    x ^= x >> 32
    x ^= x >> 16
    x ^= x >> 8
    x ^= x >> 4
    x ^= x >> 2
    x ^= x >> 1
    return x & 1

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
