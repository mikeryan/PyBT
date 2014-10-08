from struct import unpack

def decode_flags(flags):
    if len(flags) != 1:
        raise Exception("Flags must be 1 byte")

    bitfield = (
        'LE Limited Discoverable Mode',
        'LE General Discoverable Mode',
        'BR/EDR Not Supported',
        'Simultaneous LE and BR/EDR',
        'Reserved', 'Reserved', 'Reserved', 'Reserved', # silly hack
    )

    res = []
    flags = ord(flags)
    for i in range(0, len(bitfield)):
        value = bitfield[i]
        if flags & 1 << i:
            res.append(value)
    return res

def decode_uuid16(uuids):
    if len(uuids) % 2 != 0:
        raise Exception("List of 16-bit UUIDs must be a multiple of 2 bytes")
    res = []
    for i in range(0, len(uuids), 2):
        res.append('%04x' % unpack('<h', uuids[i:i+2]))
    return res

def decode_tx_power_level(power):
    if len(power) != 1:
        raise Exception("Power level must be 1 byte")
    return '%d dBm' % unpack('b', power)

def decode_slave_connection_interval_range(range):
    if len(range) != 4:
        raise Exception("Range must be 4 bytes")
    return map(lambda x: '%g ms' % (unpack('<h', x)[0] * 1.25, ), (range[0:2], range[2:]))

class GAP:
    fields = []
    types = {
        0x01: 'Flags',
        0x02: 'Incomplete List of 16-bit Service Class UUIDs',
        0x03: 'Complete List of 16-bit Service Class UUIDs',
        0x04: 'Incomplete List of 32-bit Service Class UUIDs',
        0x05: 'Complete List of 32-bit Service Class UUIDs',
        0x06: 'Incomplete List of 128-bit Service Class UUIDs',
        0x07: 'Complete List of 128-bit Service Class UUIDs',
        0x08: 'Shortened Local Name',
        0x09: 'Complete Local Name',
        0x0A: 'Tx Power Level',
        0x0D: 'Class of Device',
        0x0E: 'Simple Pairing Hash C',
        0x0F: 'Simple Pairing Randomizer',
        0x10: 'Security Manager TK Value',
        0x11: 'Security Manager Out of Band Flags',
        0x12: 'Slave Connection Interval Range',
        0x14: 'List of 16-bit Service Solicitation UUIDs',
        0x1F: 'List of 32-bit Service Solicitation UUIDs',
        0x15: 'List of 128-bit Service Solicitation UUIDs',
        0x16: 'Service Data',
        0x20: 'Service Data - 32-bit UUID',
        0x21: 'Service Data - 128-bit UUID',
        0x17: 'Public Target Address',
        0x18: 'Random Target Address',
        0x19: 'Appearance',
        0x1A: 'Advertising Interval',
        0x1B: 'LE Bluetooth Device Address',
        0x1C: 'LE Role',
        0x1D: 'Simple Pairing Hash C-256',
        0x1E: 'Simple Pairing Randomizer R-256',
        0x3D: '3D Information Data',
        0xFF: 'Manufacturer Specific Data',
    }

    decoder = {
        0x01: decode_flags,
        0x02: decode_uuid16,
        0x03: decode_uuid16,
        0x0A: decode_tx_power_level,
        0x12: decode_slave_connection_interval_range,
    }

    def __init__(self):
        pass

    def decode(self, data):
        self.fields = []
        pos = 0
        while pos < len(data):
            length = ord(data[pos])
            pos += 1
            if pos + length > len(data):
                raise Exception("Data too short (%d < %d)" % (pos + length, len(data)))
            type = ord(data[pos])
            value = data[pos+1:pos+length]
            self.fields.append((type,value))
            pos += length

    def __repr__(self):
        pretty = []
        for type, value in self.fields:
            t = self.types.get(type, '%02X' % type)
            decoder = self.decoder.get(type, lambda x: repr(x))
            pretty.append('%s: %s' % (t, decoder(value)))
        return ', '.join(pretty)

if __name__ == "__main__":
    gap = GAP()
    data = '\x02\x01\x06\x03\x03\xfa\xfe\x13\xff\xf0\x00\x0016\xac\x81\x85\xc5\xf6\xed\x00\x00\x00\x00\x00\x00\x00'
    gap.decode(data)
    print gap
    data = '\x02\x01\x04\x03\x03\x12\x18\x03\x19\xc2\x03\x0a\x09Bad Mouse'
    gap.decode(data)
    print gap
