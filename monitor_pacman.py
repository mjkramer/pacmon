#!/usr/bin/env python3

import zmq

from format import Message


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
            msg = Message.parse(raw)
            if pretty:
                print(msg)
            else:
                print(raw.hex(sep=' '))


if __name__ == '__main__':
    dump_messages()
