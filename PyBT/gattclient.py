import sys
import gevent
from gevent.fileobject import FileObject
from binascii import unhexlify
from PyBT.roles import LE_Central
from PyBT.stack import BTEvent
from PyBT.gap import GAP

from gevent.select import select
# this is hack because the above does not work
from gevent import monkey
monkey.patch_select()

DISCONNECTED = 0
CONNECTED = 1

seen = {}
state = DISCONNECTED
onconnect = []

def parse_command(f, recurse=True):
    if len(f) == 0:
        return None

    if f[0] == 'scan':
        if len(f) == 1 or f[1] == 'on':
            arg = 'on'
        elif f[1] == 'off':
            arg = 'off'
        else:
            print "Error: scan [on|off]"
            return None
        return ('scan', arg)
    if f[0] == 'connect':
        arg = None
        if len(f) == 1:
            print "Error: connect <address> [type]"
            return None
        elif len(f) == 3:
            if f[2] in ('public', 'random'):
                arg = f[2]
            else:
                print "Type must be public or random"
        return ('connect', f[1], arg)
    if f[0] == 'quit':
        return ('quit', )
    if f[0] == 'onconnect':
        if recurse:
            subcommand = parse_command(f[1:], False)
            return ('onconnect', subcommand)
        else:
            print "Cannot have onconnect within onconnect"
            return None
    if f[0] == 'write-req':
        if len(f) != 3:
            print "Error: write-req <handle> [value]"
            return None
        try:
            handle = int(f[1], base=16)
            value = unhexlify(f[2])
        except:
            print "Format error, handle is a hex int and value is a bunch of hex bytes"
            return None
        return ('write-req', handle, value)
    if f[0] == 'read':
        if len(f) != 2:
            print "Error: read <handle>"
            return None
        try:
            handle = int(f[1], base=16)
        except:
            print "Format error, handle is a hex int"
            return None
        return ('read', handle)
    if f[0] == 'eval':
        if len(f) == 1:
            print "Error: eval <python code>"
            return None
        try:
            thunk = eval('lambda: %s' % ' '.join(f[1:]))
        except Exception as e:
            print "Error: cannot eval: %s" % e
            return None
        return ('eval', thunk)
    if f[0] == 'raw':
        if len(f) != 2:
            print "Error: raw [data]"
            return None
        try:
            data = unhexlify(f[1])
        except:
            print "Format error, data is a bunch of hex bytes"
            return None
        return ('raw', data)

    print "Error: Unknown command '%s'" % f[0]
    return None

def process_command(cmd, central):
    global seen, state, onconnect

    if cmd[0] == 'scan':
        if cmd[1] == 'on':
            central.stack.scan()
        else:
            central.stack.scan_stop()
    elif cmd[0] == 'connect':
        addr, type = cmd[1:3]
        if type is None:
            type = seen.get(addr, (None,))[0] # maybe we saw it when advertising
        if type is None:
            print "Error: please give address type"
        else:
            print "Connecting.."
            central.stack.connect(addr, type)
    elif cmd[0] == 'quit':
        exit(0)
    elif cmd[0] == 'write-req':
        if state != CONNECTED:
            print "Can only write when connected!"
        else:
            central.att.write_req(handle=cmd[1], value=cmd[2])
    elif cmd[0] == 'read':
        handle = cmd[1]
        if state != CONNECTED:
            print "Can only read when connected!"
        else:
            central.att.read(handle)
    elif cmd[0] == 'onconnect':
        onconnect.append(cmd[1])
    elif cmd[0] == 'eval':
        try:
            cmd[1]()
        except Exception as e:
            print "Error running eval'd code: %s" % e
    elif cmd[0] == 'raw':
        central.stack.raw_att(cmd[1])

def command_handler(central):
    while True:
        sys.stdout.write('>>> ')
        sys.stdout.flush()

        select([sys.stdin], [], [])
        line = sys.stdin.readline()

        # handle commands
        if len(line) == 0:
            print
            exit(0) # hack for control-D
        line = line.strip()
        cmd = parse_command(line.split())
        if cmd is not None:
            process_command(cmd, central)

def dump_gap(data):
    if len(data) > 0:
        try:
            gap = GAP()
            gap.decode(data)
            print "GAP: %s" % gap
        except Exception as e:
            print e
            pass

def socket_handler(central):
    global seen, state, onconnect

    # handle events
    while True:
        select([central.stack], [], [])
        event = central.stack.handle_data()
        if event.type == BTEvent.SCAN_DATA:
            addr, type, data = event.data
            print "Saw %s (%s)" % (addr, "public" if type == 0 else "random")
            if addr in seen:
                if len(data) > len(seen[addr][1]):
                    seen[addr] = (type, data)
                    dump_gap(data)
            else:
                seen[addr] = (type, data)
                dump_gap(data)

        elif event.type == BTEvent.CONNECTED:
            state = CONNECTED
            print "Connected!"
            if len(onconnect) > 0:
                print "Running onconnect comands"
                for i in onconnect:
                    process_command(i, central)
                onconnect = []
        elif event.type == BTEvent.DISCONNECTED:
            state = DISCONNECTED
            print "Disconnected"
        elif event.type != BTEvent.NONE:
            print event

def main():
    central = LE_Central(adapter=0)
    gevent.spawn(socket_handler, central)
    gevent.spawn(command_handler, central)
    gevent.wait()

if __name__ == '__main__':
    main()
