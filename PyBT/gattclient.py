import os
import sys
import code
from threading import Thread
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

central = None
seen = {}
state = DISCONNECTED
onconnect = []

def debug(msg):
    if os.getenv("DEBUG"):
        sys.stdout.write(msg)
        sys.stdout.write("\n")

class InvalidCommand(Exception):
    pass

class UnknownCommand(Exception):
    pass

class CommandModule(object):
    """Dumb container for commands"""
    @staticmethod
    def scan(*args):
        if len(args) == 0 or args[0] == 'on':
            arg = 'on'
        elif args[0] == 'off':
            arg = 'off'
        else:
            raise InvalidCommand("scan [on|off]")
        return ('scan', arg)

    @staticmethod
    def connect(*args):
        def fail():
            raise InvalidCommand("connect <address> [public|random]")

        arg = None
        if len(args) == 1:
            pass
        elif len(args) == 2:
            if args[1] in ('public', 'random'):
                arg = args[1]
            else:
                fail()
        else:
            fail()
        return ('connect', args[0], arg)

    @staticmethod
    def quit(*args):
        return ('quit', )

    @staticmethod
    def write_req(*args):
        if len(args) != 2:
            raise InvalidCommand("write-req <handle> <value>")
        try:
            handle = int(args[0], base=16)
            value = unhexlify(args[1])
        except:
            raise InvalidCommand("Format error, handle is a hex int and value is a bunch of hex bytes")
        return ('write-req', handle, value)

    @staticmethod
    def write_cmd(*args):
        if len(args) != 2:
            raise InvalidCommand("write-cmd <handle> <value>")
        try:
            handle = int(args[0], base=16)
            value = unhexlify(args[1])
        except:
            raise InvalidCommand("Format error, handle is a hex int and value is a bunch of hex bytes")
        return ('write-cmd', handle, value)

    @staticmethod
    def read(*args):
        if len(args) != 1:
            raise InvalidCommand("read <handle>")
        try:
            handle = int(args[0], base=16)
        except:
            raise InvalidCommand("Format error, handle is a hex int")
        return ('read', handle)

    @staticmethod
    def raw(*args):
        if len(args) != 1:
            print "Error: raw [data]"
            return None
        try:
            data = unhexlify(args[0])
        except:
            print "Format error, data is a bunch of hex bytes"
            return None
        return ('raw', data)

    @staticmethod
    def onconnect(*args):
        subcommand = parse_command(args, False)
        if subcommand[0] == 'onconnect':
            raise InvalidCommand("Can't nest oncommands")
        return ('onconnect', subcommand)


COMMANDS = {
    'scan': CommandModule.scan,
    'connect': CommandModule.connect,
    'quit': CommandModule.quit,
    'write-req': CommandModule.write_req,
    'write-cmd': CommandModule.write_cmd,
    'read': CommandModule.read,
    'oncommand': CommandModule.onconnect,
}

def parse_command(f, recurse=True):
    if len(f) == 0:
        return None
    cmd_name = f[0]
    try:
        cmd = COMMANDS[cmd_name](*f[1:])
        return cmd
    except IndexError:
        pass # Ignore people mushing return
    except KeyError as e:
        print "Error: Unknown command '%s'" % e.args[0]
        raise UnknownCommand("unknown: %s" % e.args[0])
    except InvalidCommand as e:
        print(repr(e)) # TODO Deal more gracefully

def process_command(cmd):
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
    elif cmd[0] == 'write-req' or cmd[0] == 'write-cmd':
        if state != CONNECTED:
            print "Can only write when connected!"
        else:
            if cmd[0] == 'write-req':
                central.att.write_req(handle=cmd[1], value=cmd[2])
            else:
                central.att.write_cmd(handle=cmd[1], value=cmd[2])
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

def command_handler():
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
            process_command(cmd)

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

        elif event.type == BTEvent.ATT_DATA:
            pkt = event.data
            # ack handle value notification
            if pkt.opcode == 0x1d:
                central.stack.raw_att("\x1e")
            print event
        elif event.type != BTEvent.NONE:
            print event


orig_runsource = code.InteractiveConsole.runsource
def runsource(self, source, filename='<input>', symbol='single', encode=True):
    # Try parsing it as a gatt client thing, then fall back to python
    debug("[-] %s" % repr(source.split()))
    try:
        cmd = parse_command(source.split())
    except UnknownCommand:
        # XXX uncomment me to make this into a python repl
        # return orig_runsource(self, source)
        return None

    if cmd is not None:
        debug("[-] %s" % repr(cmd))
        process_command(cmd)

def main():
    global central
    central = LE_Central(adapter=0)
    gevent.spawn(socket_handler, central)

    code.InteractiveConsole.runsource = runsource
    Thread(target=code.interact, kwargs={'local': locals()}).start()

    gevent.wait()

if __name__ == '__main__':
    main()
