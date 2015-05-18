from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor

import logging

PORT = 6667


class PseudoIRC(LineReceiver):

    def __init__(self):
        pass

    def connectionMade(self):
        logging.info("Got connection")

    def connectionLost(self, reason):
        logging.info("Lost connection")

    def lineReceived(self, line):
        logging.info("Received line: %s" % line)


class PseudoIRCFactory(Factory):

    def __init__(self):
        self.channels = {
            '#foo': [],
            '#bar': [],
        }
        self.nicks = {}

    def buildProtocol(self, addr):
        return PseudoIRC()


logging.basicConfig(level=logging.INFO)

reactor.listenTCP(PORT, PseudoIRCFactory())
logging.info("Server listening on port %d" % PORT)

reactor.run()
