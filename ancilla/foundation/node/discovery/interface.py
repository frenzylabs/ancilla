"""Interface class for Chapter on Distributed Computing

This implements an "interface" to our network of nodes
"""

import time
import uuid
from threading import Thread

import zmq
# from zmq.eventloop.ioloop import PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop, PeriodicCallback
import asyncio

from tornado.platform.asyncio import AnyThreadEventLoopPolicy

from .udp import UDP 

# =====================================================================
# Synchronous part, works in our application thread

def pipe(ctx):
    """create an inproc PAIR pipe"""
    a = ctx.socket(zmq.PAIR)
    b = ctx.socket(zmq.PAIR)
    url = "inproc://%s" % uuid.uuid1()
    a.bind(url)
    b.connect(url)
    return a, b

class Interface(object):
    """Interface class.

    Just starts a UDP ping agent in a background thread."""
    ctx = None      # Our context
    pipe = None     # Pipe through to agent

    def __init__(self, node):
        print(f"START UDP PING AGENT")
        self.node = node
        self.ctx = zmq.Context()
        p0, p1 = pipe(self.ctx)
        self.agent = InterfaceAgent(self.ctx, self.node, p1)
        self.agent_thread = Thread(target=self.agent.start)
        self.agent_thread.start()
        self.pipe = p0

    def stop(self):
        self.pipe.close()
        self.agent.stop()
        self.ctx.term()

    def send(self, evt):
        self.pipe.send_multipart(evt)
        
    def recv(self):
        """receive a message from our interface"""
        return self.pipe.recv_multipart()


# =====================================================================
# Asynchronous part, works in the background

PING_PORT_NUMBER    = 9999
PING_INTERVAL       = 1.0  # Once per second
PEER_EXPIRY         = 5.0  # Five seconds and it's gone
UUID_BYTES          = 32

class Peer(object):

    uuid = None
    expires_at = None

    def __init__(self, uuid):
        self.uuid = uuid
        self.is_alive()

    def is_alive(self):
        """Reset the peers expiry time

        Call this method whenever we get any activity from a peer.
        """
        self.expires_at = time.time() + PEER_EXPIRY


class InterfaceAgent(object):
    """This structure holds the context for our agent so we can
    pass that around cleanly to methods that need it
    """

    ctx = None                 # ZMQ context
    pipe = None                # Pipe back to application
    udp = None                 # UDP object
    uuid = None                # Our UUID as binary blob
    peers = None               # Hash of known peers, fast lookup


    def __init__(self, ctx, node, pipe, loop=None):
        self.ctx = ctx
        self.node = node
        self.pipe = pipe
        self.loop = loop
        self.udp = UDP(PING_PORT_NUMBER)
        self.uuid = uuid.uuid4().hex.encode('utf8')
        self.peers = {}

    def stop(self):
        self.pipe.close()
        self.loop.stop()

    def __del__(self):
        try:
            self.stop()
        except:
            pass

    def start(self):
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

        if self.loop is None:
            if not IOLoop.current(instance=False):
                # evloop = asyncio.new_event_loop()
                # asyncio.set_event_loop(evloop)
                self.loop = IOLoop()          
                # loop.make_current()
                # asyncio.set_event_loop(loop)
                print(f'INIT LOOP = {self.loop}')
            else:
                self.loop = IOLoop.current()
                print(f'INIT LOOP 2= {self.loop}')


        loop = self.loop
        loop.add_handler(self.udp.handle.fileno(), self.handle_beacon, loop.READ)
        stream = ZMQStream(self.pipe, loop)
        stream.on_recv(self.control_message)
        pc = PeriodicCallback(self.send_ping, PING_INTERVAL * 3000, 0.1)
        pc.start()
        pc = PeriodicCallback(self.reap_peers, PING_INTERVAL * 3000, 0.1)
        pc.start()
        loop.start()

    def send_ping(self, *a, **kw):
        try:
            print(f'Self node #{self.node.identity}')
            self.udp.send([self.node.identity, self.uuid])
        except Exception as e:
            self.loop.stop()

    def control_message(self, event):
        """Here we handle the different control messages from the frontend."""
        print("control message: %s"%event)

    def handle_beacon(self, fd, event):
        uuid = self.udp.recv(UUID_BYTES)
        print(f"Handle beacon {uuid}")
        if uuid in self.peers:
            self.peers[uuid].is_alive()
        else:
            self.peers[uuid] = Peer(uuid)
            self.pipe.send_multipart([b'JOINED', uuid])

    def reap_peers(self):
        now = time.time()
        for peer in list(self.peers.values()):
            if peer.expires_at < now:
                print("reaping %s" % peer.uuid, peer.expires_at, now)
                self.peers.pop(peer.uuid)
                self.pipe.send_multipart([b'LEFT', peer.uuid])
