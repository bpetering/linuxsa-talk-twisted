from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

import logging

PORT = 6667


class PseudoIRC(LineReceiver):

    def __init__(self, channels, nicks, protocols):
        self.channels = channels
        self.nicks = nicks
        self.protocols = protocols
        self.nick = None        # username
        self.channel = None     # current channel

    def connectionMade(self):
        logging.info("Got connection")

    def connectionLost(self, reason):
        self.handle_QUIT()

    def sendResponse(self, line):
        self.sendLine('-- ' + line)

    def broadcastLine(self, line):
        # Send line to all users in current channels
        send_nicks = set()
        for nick in self.channels[self.channel]:
            # Don't send our message back to us
            if nick != self.nick:
                send_nicks.add(nick)
        for nick in send_nicks:
            self.protocols[nick].sendLine('%s <%s> %s' % (
                                          self.channel, self.nick, line))

    def lineReceived(self, line):
        if not line:
            return
        if line[0] != "/":
            # Normal message - send to all users in current channel
            self.broadcastLine(line)
            return

        # Otherwise it's a command
        line = line[1:]                 # strip /
        parts = line.split()            # syntax: <cmd> [argument]
        cmd = parts[0].lower()

        if cmd not in ("users", "list", "quit",
                       "nick", "join", "chan", "part"):
            self.sendResponse("Bad command: %s" % cmd)
            return

        if cmd == "users":
            self.handle_USERS()
            return

        if cmd == "list":
            self.handle_LIST()
            return

        if cmd == "quit":
            # Nick/channel handling logic not here, since
            # we want to do same if TCP connection dies
            self.transport.loseConnection()
            logging.info("User %s quit" % self.nick)
            return

        # All other commands need arg
        if len(parts) == 1:
            self.sendResponse("Command /%s needs argument" % cmd)
            return
        arg = parts[1]

        if cmd == "nick":
            self.handle_NICK(arg)

        if cmd == "join":
            self.handle_JOIN(arg)
            return

        if cmd == "chan":
            self.handle_CHAN(arg)
            return

        if cmd == "part":
            self.handle_PART(arg)
            return


    def handle_LIST(self):
        self.sendResponse("Channels:")
        for chan in sorted(self.channels.keys()):
            self.sendResponse(chan)
        self.sendResponse("End of channel list")


    def handle_USERS(self):
        self.sendResponse("Users:")
        for nick in sorted(self.nicks.keys()):
            self.sendResponse(nick)
        self.sendResponse("End of users list")

    def handle_QUIT(self):
        if self.nick is None:
            logging.info("Lost connection")
            return
        logging.info("User %s quit" % self.nick)
        del self.nicks[self.nick]
        # If user was last in channel, remove channel
        for chan in self.channels.keys():
            if self.channels[chan] == set([self.nick]):
                del self.channels[chan]
                logging.info("Removed channel %s, user %s last" % (
                             chan, self.nick))

    def handle_NICK(self, arg):
        if arg in self.nicks:
            self.sendResponse("Nick '%s' already in use" % arg)
            return
        self.nick = arg
        self.nicks[self.nick] = set()
        self.protocols[self.nick] = self
        self.sendResponse("Set nick: %s" % self.nick)
        logging.info("User set nick '%s'" % self.nick)

    def handle_JOIN(self, arg):
        if not self.nick:
            self.sendLine("You must set a nick first (/nick)")
            return
        if arg not in self.channels:
            # Create channel if it doesn't exist
            self.channels[arg] = set()
            logging.info("Created channel %s" % arg)
        self.channels[arg].add(self.nick)
        self.nicks[self.nick].add(arg)
        self.channel = arg
        self.sendResponse("Joined %s" % arg)
        logging.info("User %s joined %s" % (self.nick, arg))

    def handle_CHAN(self, arg):
        # Set current channel for user
        if not self.nick:
            self.sendLine("You must set a nick first (/nick)")
            return
        if arg not in self.nicks[self.nick]:
            self.sendResponse("You aren't joined to channel %s" % arg)
            return
        self.channel = arg
        self.sendResponse("Set channel to %s" % arg)
        logging.info("User %s set channel %s" % (self.nick, arg))

    def handle_PART(self, arg):
        if arg not in self.nicks[self.nick]:
            self.sendResponse("You aren't joined to channel %s" % arg)
            return
        self.nicks[self.nick].remove(arg)
        self.channels[arg].remove(self.nick)
        self.sendResponse("Left %s" % arg)
        logging.info("User %s left %s" % (self.nick, arg))
        # If was last user, remove channel
        if not self.channels[arg]:
            del self.channels[arg]
            logging.info("Removed channel %s" % arg)


class PseudoIRCFactory(Factory):

    def __init__(self):
        self.channels = {}      # dict, channel => set of nicks
        self.nicks = {}         # dict, nick => set of channels
        self.protocols = {}     # dict, nick => protocol

    def buildProtocol(self, addr):
        return PseudoIRC(self.channels, self.nicks, self.protocols)


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

reactor.listenTCP(PORT, PseudoIRCFactory())
logging.info("Server listening on port %d" % PORT)

reactor.run()
