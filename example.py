#!/usr/bin/env python

# Copyright 2016 Mike Ryan
#
# This file is part of PyBT and is available under the MIT license. Refer to
# LICENSE for details.

import BDAddr
from BluetoothSocket import BluetoothSocket, hci_devba
import socket

my_addr = hci_devba(0) # get from HCI0
dest = BDAddr.BDAddr("00:11:22:33:44:55")
addr_type = BDAddr.TYPE_LE_PUBLIC

# open L2CAP socket, then bind and connect on CID 4, GATT
sock = BluetoothSocket(socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP)
sock.bind_l2(0, my_addr, cid=4, addr_type=BDAddr.TYPE_LE_PUBLIC)
sock.connect_l2(0, dest, cid=4, addr_type=addr_type)

# send a write request (opcode 0x12) to handle 0x0037 with value 0x1122
sock.send("\x12\x37\x00\x11\x22")
r = sock.recv(30)
print repr(r)
