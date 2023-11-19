#!/usr/bin/env python3

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
