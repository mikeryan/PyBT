# Copyright 2016 Mike Ryan
#
# This file is part of PyBT and is available under the MIT license. Refer to
# LICENSE for details.

# address types
TYPE_BREDR      = 0
TYPE_LE_PUBLIC  = 1
TYPE_LE_RANDOM  = 2

class BDAddr():
    def __init__(self, addr):
        # Create a BD ADDR
        # addr can be:
        #  - ASCII string representation ("00:11:22:33:44:55")
        #  - 48-bit string of raw bytes ("\x00\x11\x22\x33\x44\x55")
        #  - another BD ADDR

        if isinstance(addr, str):
            if len(addr) == 6:
                self.parts = self._parse_raw(addr)
            else:
                self.parts = self._parse_str(addr)
        elif isinstance(addr, BDAddr):
            self.parts = addr.parts
        else:
            raise TypeError("BDAddr must be a string or address")

    def _parse_raw(self, addr):
        return [ord(x) for x in addr[::-1]]

    def _parse_str(self, addr):
        parts = addr.split(':')
        if len(parts) != 6:
            raise TypeError("Expecting 6 ':', got %d" % len(parts))
        outparts = []
        for part in parts:
            intval = int(part, 16)
            if intval < 0 or intval > 255:
                raise TypeError("Hex value out of range")
            outparts.append(intval)
        return outparts

    def raw_string(self):
        # Returns a 48-bit string of raw bytes ("\x00\x11\x22\x33\x44\x55")
        return ''.join(chr(x) for x in self.parts)

    def le_string(self):
        # Returns a 48-bit string of raw bytes, little endian first
        return ''.join(chr(x) for x in reversed(self.parts))

    def __str__(self):
        return ':'.join(format(x, '02X') for x in self.parts)

    def __repr__(self):
        return self.__str__()

if __name__ == "__main__":
    a = BDAddr("00:11:22:33:44:55")
    print a
    print repr(a.raw_string())
    print repr(a.le_string())
