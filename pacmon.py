#!/usr/bin/python2
'''
A lightweight, standalone python script to interface with the pacman servers
See help text for more details::

    python2 pacman_util.py --help

'''
import zmq
import struct
import time
import argparse
import sys
import socket
import curses

_SERVERS = dict(
    ECHO_SERVER = 'tcp://{ip}:5554',
    CMD_SERVER = 'tcp://{ip}:5555',
    DATA_SERVER = 'tcp://{ip}:5556'
    )

HEADER_LEN = 8
WORD_LEN = 16

MSG_TYPE = {
    'DATA': b'D',
    'REQUEST': b'?',
    'REPLY': b'!'
}
MSG_TYPE_INV = dict([(val, key) for key,val in MSG_TYPE.items()])

WORD_TYPE = {
    'DATA': b'D',
    'TRIG': b'T',
    'SYNC': b'S',
    'PING': b'P',
    'WRITE': b'W',
    'READ': b'R',
    'ERROR': b'E'
}
WORD_TYPE_INV = dict([(val, key) for key,val in WORD_TYPE.items()])

_VERBOSE = False

_msg_header_fmt = '<cLxH'
_msg_header_struct = struct.Struct(_msg_header_fmt)

_word_fmt = {
    'DATA': '<cBLxxQ',
    'TRIG': '<cBxxL8x',
    'SYNC': '<c2BxL8x',
    'PING': '<c15x',
    'WRITE': '<c3xL4xL',
    'READ': '<c3xL4xL',
    'ERROR': '<cB14s'
}
_word_struct = dict([
    (key, struct.Struct(fmt))
    for key,fmt in _word_fmt.items()
])

# to count the total number of instances of each packet type
_packet_type_count = dict([(packet_type,0) for packet_type in WORD_TYPE.keys()])

_data_packet_count_per_ioc = dict([(ioc,[0,0,0,0,0]) for ioc in range(1,33,1)])
_config_packet_count_per_ioc = dict([(ioc,[0,0,0,0,0,0]) for ioc in range(1,33,1)])

def format_header(msg_type, msg_words):
    return _msg_header_struct.pack(MSG_TYPE[msg_type], int(time.time()), msg_words)

def format_word(word_type, *data):
    return _word_struct[word_type].pack(WORD_TYPE[word_type],*data)

def parse_header(header):
    data = _msg_header_struct.unpack(header)
    return (MSG_TYPE_INV[data[0]],) + tuple(data[1:])

def parse_word(word):
    word_type = WORD_TYPE_INV[word[0:1]]
    data = _word_struct[word_type].unpack(word)
    return (word_type,) + tuple(data[1:])

def format_msg(msg_type, msg_words):
    msg_bytes = format_header(msg_type, len(msg_words))
    for msg_word in msg_words:
        msg_bytes += format_word(*msg_word)
    return msg_bytes

def parse_msg(msg):
    header = parse_header(msg[:HEADER_LEN])
    words = [
        parse_word(msg[i:i+WORD_LEN])
        for i in range(HEADER_LEN,len(msg),WORD_LEN)
    ]
    return header, words

def print_larpix_bits(word):
    if word[-1] == 'L': word = word[:-1]
    word_int = _int_parser(word)
    bit_msg = format(word_int,'064b')
    bit_msg = bit_msg[::-1]
    bit_arr = list(bit_msg)
    return bit_arr

def print_msg(msg):
    header, words = parse_msg(msg)
    header_strings, word_strings = list(), list()
    header_strings.extend(header)
    for word in words:
        word_string = list()
        if word[0] == 'DATA':
            word_string.extend(word[:3])
            word_string.append(hex(word[3]))
        elif word[0] in ('TRIG', 'SYNC'):
            word_string.append(word[0])
            word_string.append(repr(word[1]))
            word_string.extend(word[2:])
        elif word[0] in ('WRITE', 'READ'):
            word_string.append(word[0])
            word_string.append(hex(word[1]))
            word_string.append(hex(word[2]))
        elif word[0] in ('PING','ERROR'):
            word_string.extend(word)
        word_strings.append(word_string)
    print(' | '.join([repr(val) for val in header_strings]) + '\n\t'
        + '\n\t'.join([' | '.join([repr(val) for val in word_string])for word_string in word_strings]))

def run_console(stdscr,start,msg=None):

    win_width = 90
    win_height = 80

    show_data = True
    show_config = False

    window = curses.newwin(win_height,win_width,0,0)
    window.clear()
    #window.nodelay(1)

    words = []

    if msg != None: header_msg, words = parse_msg(msg)

    line_num = 0

    # for debugging:
    #if len(words)>0:
    #    word = hex(words[-1][-1])
    #    larpix_bits = print_larpix_bits(word)
    #    parity = 1 - (larpix_bits[slice(0,63)].count('1')%2)
    #    window.addstr(10,30,str(larpix_bits[slice(0,2)]))
    #    window.addstr(8,25,str(larpix_bits))
    #    window.addstr(8,25,str(larpix_bits[63]))
    #    window.addstr(8,28,str(parity))
    #    window.addstr(25,30,str(word))
    #    window.addstr(30,30,str(len(larpix_bits)))

    header = 'Packet monitoring on '+socket.gethostname()+' beginning: '+time.strftime("%B %e, %Y at %H:%M:%S",time.localtime(start))+'.'
    window.addstr(line_num,0,header)
    line_num+=1
    header = 'last updated: '+time.strftime("%B %e, %Y at %H:%M:%S",time.localtime())+'.'
    window.addstr(line_num,27,header)
    line_num+=2
    window.addstr(line_num,1,'Pacman packet counts:')
    line_num+=1
    window.hline(line_num,1,curses.ACS_HLINE,20)
    line_num+=1
    window.vline(line_num,1,curses.ACS_VLINE,7)
    window.vline(line_num,8,curses.ACS_VLINE,7)
    window.vline(line_num,20,curses.ACS_VLINE,7)
    for type_it, packet_type in enumerate(_packet_type_count.keys()):
        window.addstr(line_num,3,packet_type)
        window.addstr(line_num,10,str(_packet_type_count[packet_type]))
        line_num+=1
    window.hline(line_num,1,curses.ACS_HLINE,20)

    if show_data:
        line_num+=2
        window.addstr(line_num,1,'Data packets per I/O channel:')
        line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,88)
        line_num+=1
        window.vline(line_num,1,curses.ACS_VLINE,35)
        window.vline(line_num,13,curses.ACS_VLINE,35)
        window.vline(line_num,28,curses.ACS_VLINE,35)
        window.vline(line_num,43,curses.ACS_VLINE,35)
        window.vline(line_num,58,curses.ACS_VLINE,35)
        window.vline(line_num,73,curses.ACS_VLINE,35)
        window.vline(line_num,88,curses.ACS_VLINE,35)

        window.addstr(line_num,3,"I/O Chan")
        window.addstr(line_num,15,'Total')
        window.addstr(line_num,30,'Valid Parity')
        window.addstr(line_num,45,'Inval Parity')
        window.addstr(line_num,60,'Downstream')
        window.addstr(line_num,75,'Upstream')
        line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,88)
        line_num+=1

        for ioc_it, ioc in enumerate(_data_packet_count_per_ioc.keys()):
            window.addstr(line_num,7,str(ioc))
            window.addstr(line_num,15,str(_data_packet_count_per_ioc[ioc][0]))
            if _data_packet_count_per_ioc[ioc][0]>0:
                window.addstr(line_num,30,str(_data_packet_count_per_ioc[ioc][1])+' ({:.0f}%)'.format(100.*_data_packet_count_per_ioc[ioc][1]/_data_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,45,str(_data_packet_count_per_ioc[ioc][2])+' ({:.0f}%)'.format(100.*_data_packet_count_per_ioc[ioc][2]/_data_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,60,str(_data_packet_count_per_ioc[ioc][3])+' ({:.0f}%)'.format(100.*_data_packet_count_per_ioc[ioc][3]/_data_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,75,str(_data_packet_count_per_ioc[ioc][4])+' ({:.0f}%)'.format(100.*_data_packet_count_per_ioc[ioc][4]/_data_packet_count_per_ioc[ioc][0]))
            else:
                window.addstr(line_num,30,str(_data_packet_count_per_ioc[ioc][1]))
                window.addstr(line_num,45,str(_data_packet_count_per_ioc[ioc][2]))
            window.addstr(line_num,60,str(_data_packet_count_per_ioc[ioc][3]))
            window.addstr(line_num,75,str(_data_packet_count_per_ioc[ioc][4]))
            line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,88)

    elif show_config:
        line_num+=2
        window.addstr(line_num,1,'Config packets per I/O channel:')
        line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,84)
        line_num+=1
        window.vline(line_num,1,curses.ACS_VLINE,35)
        window.vline(line_num,12,curses.ACS_VLINE,35)
        window.vline(line_num,24,curses.ACS_VLINE,35)
        window.vline(line_num,36,curses.ACS_VLINE,35)
        window.vline(line_num,48,curses.ACS_VLINE,35)
        window.vline(line_num,60,curses.ACS_VLINE,35)
        window.vline(line_num,72,curses.ACS_VLINE,35)
        window.vline(line_num,84,curses.ACS_VLINE,35)

        window.addstr(line_num,3,"I/O Chan")
        window.addstr(line_num,14,'Total')
        window.addstr(line_num,26,'Inval Par')
        window.addstr(line_num,38,'DS READ')
        window.addstr(line_num,50,'DS WRITE')
        window.addstr(line_num,62,'US READ')
        window.addstr(line_num,74,'US WRITE')
        line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,84)
        line_num+=1

        for ioc_it, ioc in enumerate(_config_packet_count_per_ioc.keys()):
            window.addstr(line_num,4,str(ioc))
            window.addstr(line_num,14,str(_config_packet_count_per_ioc[ioc][0]))
            if _config_packet_count_per_ioc[ioc][0]>0:
                window.addstr(line_num,26,str(_config_packet_count_per_ioc[ioc][1])+' ({:.0f}%)'.format(100.*_config_packet_count_per_ioc[ioc][1]/_config_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,38,str(_config_packet_count_per_ioc[ioc][2])+' ({:.0f}%)'.format(100.*_config_packet_count_per_ioc[ioc][2]/_config_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,50,str(_config_packet_count_per_ioc[ioc][3])+' ({:.0f}%)'.format(100.*_config_packet_count_per_ioc[ioc][3]/_config_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,62,str(_config_packet_count_per_ioc[ioc][4])+' ({:.0f}%)'.format(100.*_config_packet_count_per_ioc[ioc][4]/_config_packet_count_per_ioc[ioc][0]))
                window.addstr(line_num,74,str(_config_packet_count_per_ioc[ioc][5])+' ({:.0f}%)'.format(100.*_config_packet_count_per_ioc[ioc][5]/_config_packet_count_per_ioc[ioc][0]))
            else:
                window.addstr(line_num,26,str(_config_packet_count_per_ioc[ioc][1]))
                window.addstr(line_num,38,str(_config_packet_count_per_ioc[ioc][2]))
            window.addstr(line_num,50,str(_config_packet_count_per_ioc[ioc][3]))
            window.addstr(line_num,62,str(_config_packet_count_per_ioc[ioc][4]))
            window.addstr(line_num,74,str(_config_packet_count_per_ioc[ioc][5]))
            line_num+=1
        window.hline(line_num,1,curses.ACS_HLINE,84)

#
#    # for debugging:
#    line_num=38
#    if msg != None:
#        header_strings, word_strings = list(), list()
#        header_strings.extend(header_msg)
#        for word in words:
#            word_string = list()
#            if word[0] == 'DATA':
#                word_string.extend(word[:3])
#                word_string.append(hex(word[3]))
#            elif word[0] in ('TRIG', 'SYNC'):
#                word_string.append(word[0])
#                word_string.append(repr(word[1]))
#                word_string.extend(word[2:])
#            elif word[0] in ('WRITE', 'READ'):
#                word_string.append(word[0])
#                word_string.append(hex(word[1]))
#                word_string.append(hex(word[2]))
#            elif word[0] in ('PING','ERROR'):
#                word_string.extend(word)
#            word_strings.append(word_string)
#        message = ' | '.join([repr(val) for val in header_strings]) + '\n\t'+ '\n\t'.join([' | '.join([repr(val) for val in word_string])for word_string in word_strings])
#
#        line_num+=2
#    if msg!=None: window.addstr(line_num,0,message)


    window.refresh()
    #window.getch() 

def main(stdscr):
    try:
        # create ZMQ context and sockets
        ctx = zmq.Context()
        data_socket = ctx.socket(zmq.SUB)
        #cmd_socket = ctx.socket(zmq.SUB)
        echo_socket = ctx.socket(zmq.SUB)
        socket_opts = [
            (zmq.LINGER, 1000),
            (zmq.RCVTIMEO, 1000*11),
            (zmq.SNDTIMEO, 1000*11)
        ]
        for opt in socket_opts:
            data_socket.setsockopt(*opt)
            #cmd_socket.setsockopt(*opt)
            echo_socket.setsockopt(*opt)

        # connect to pacman data server
        data_server = 'DATA_SERVER'
        data_connection = _SERVERS[data_server].format(ip='127.0.0.1')
        data_socket.connect(data_connection)
        data_socket.setsockopt(zmq.SUBSCRIBE, b'')

        # connect to pacman command server
        #cmd_server = 'CMD_SERVER'
        #cmd_connection = _SERVERS[cmd_server].format(ip='127.0.0.1')
        #cmd_socket.connect(cmd_connection)
        #cmd_socket.setsockopt(zmq.SUBSCRIBE, b'')

        # connect to pacman command server
        echo_server = 'ECHO_SERVER'
        echo_connection = _SERVERS[echo_server].format(ip='127.0.0.1')
        echo_socket.connect(echo_connection)
        echo_socket.setsockopt(zmq.SUBSCRIBE, b'')

        # initialize poll set
        poller = zmq.Poller()
        poller.register(data_socket,zmq.POLLIN)
        #poller.register(cmd_socket,zmq.POLLIN)
        poller.register(echo_socket,zmq.POLLIN)

        passed_time = 0
        start_time = time.time()
        run_console(stdscr, start_time)
        last = time.time()

        #while passed_time < 100:
        while True:
            #passed_time = time.time() - start_time
            sockets = dict(poller.poll())
            if data_socket in sockets and sockets[data_socket] == zmq.POLLIN:
                msg = data_socket.recv()
            #if cmd_socket in sockets and sockets[cmd_socket] == zmq.POLLIN:
            #    msg = cmd_socket.recv()
            if echo_socket in sockets and sockets[echo_socket] == zmq.POLLIN:
                msg = echo_socket.recv()

            msg_header, msg_words = parse_msg(msg)

            # modify counters based on message content:
            for word in msg_words:
                is_config_read_packet = False
                is_config_write_packet = False
                if word[0] in _packet_type_count.keys():
                    larpix_bits = print_larpix_bits(hex(word[-1]))
                    if word[0] == 'DATA' and larpix_bits[slice(0,2)] == ['0','0']:
                        _packet_type_count['DATA'] += 1
                    elif word[0] == 'DATA' and larpix_bits[slice(0,2)] == ['1','0']:
                        _packet_type_count['WRITE'] += 1
                        is_config_write_packet = True
                    elif word[0] == 'DATA' and larpix_bits[slice(0,2)] == ['1','1']:
                        _packet_type_count['READ'] += 1
                        is_config_read_packet = True
                    elif word[0] == 'DATA' and larpix_bits[slice(0,2)] == ['0','1']:
                        _packet_type_count['ERROR'] += 1
                    else:
                        _packet_type_count[word[0]] += 1
                else:
                    print('unknown packet type!')
                    exit
                if word[0] == 'DATA' and word[1] in _data_packet_count_per_ioc.keys():
                    _data_packet_count_per_ioc[word[1]][0] += 1 # total packets per channel
                    larpix_bits = print_larpix_bits(hex(word[-1]))
                    parity = 1 - (larpix_bits[slice(0,63)].count('1')%2)
                    valid_parity = parity == int(larpix_bits[63])
                    if valid_parity: # valid parity packets per channel
                        _data_packet_count_per_ioc[word[1]][1] += 1
                        if is_config_read_packet:   # read config packet
                            _config_packet_count_per_ioc[word[1]][1] += 1
 
                    else:  # invalid parity packets per channel
                        _data_packet_count_per_ioc[word[1]][2] += 1
                        if is_config_read_packet or is_config_write_packet: # invalid_pary config
                            _config_packet_count_per_ioc[word[1]][1] += 1
                    if larpix_bits[62] == '1':   # downstream packet
                        _data_packet_count_per_ioc[word[1]][3] += 1
                        if is_config_read_packet:    # DS read config packet
                            _config_packet_count_per_ioc[word[1]][2] += 1
                        elif is_config_write_packet: # DS write config packet
                            _config_packet_count_per_ioc[word[1]][3] += 1
                    elif larpix_bits[62] == '0': # upstream packet
                        _data_packet_count_per_ioc[word[1]][4] += 1
                        if is_config_read_packet:    # US read config packet
                            _config_packet_count_per_ioc[word[1]][4] += 1
                        elif is_config_write_packet: # US write config packet
                            _config_packet_count_per_ioc[word[1]][5] += 1
                    if is_config_read_packet:   # read config packet
                        _config_packet_count_per_ioc[word[1]][2] += 1
                    if is_config_write_packet:   # write config packet
                        _config_packet_count_per_ioc[word[1]][3] += 1
            # update information printed to screen
            if time.time() - last > 1:
                run_console(stdscr, start_time, msg)
                last = time.time()

        # close the socket
        data_socket.setsockopt(zmq.UNSUBSCRIBE, b'')
        print('disconnect from {} @ {}...'.format(server, connection))
        data_socket.disconnect(connection)

    except Exception as err:
        # handle timeouts
        print('closing sockets')
        if isinstance(err,zmq.error.Again):
            print('timed out')
        else:
            raise
    finally:
        # cleanup
        data_socket.close()
        ctx.destroy()

def _int_parser(s):
    if len(s) >= 2:
        if s[:2] == '0x' or s[:1] == 'x':
            return int(s.split('x')[-1],16)
        elif s[:2] == '0b' or s[:1] == 'b':
            return int(s.split('b')[-1],2)
    return int(s)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='''
        A stand-alone utility script to monitor the PACMAN.
        ''')

    curses.wrapper(main)
