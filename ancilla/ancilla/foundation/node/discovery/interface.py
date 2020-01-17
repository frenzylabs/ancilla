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
import json

import socket
import netifaces

from .udp import UDP 

from ...utils.service_json_encoder import ServiceJsonEncoder
from ..response import AncillaError
from ...data.models import Node
from .beacon import Beacon
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
    requestpipe = None
    beacon = None
    agent_thread = None
    agent = None
    networkcb = None
    nodecb = None
    current_address = None

    def __init__(self, node):
        print(f"START UDP PING AGENT")
        self.cached_peers = [] 
        self.node = node
        self.beacon = Beacon(self.node.name)
        # self.udp = UDP(PING_PORT_NUMBER)
        
        self.current_address = self.check_interface_addresses()
        self.beacon.address = self.current_address
        
        self.networkcb = PeriodicCallback(self.check_network, PING_INTERVAL * 2000, 0.2)
        self.nodecb = PeriodicCallback(self.check_nodes, PING_INTERVAL * 4000, 0.1)
        self.run(self.node.settings.discovery)
        # self.run(False)

        
        
        # if self.node.settings.discovery == True:
        #     self.start()

            
    def run(self, val):
        if val:
            self.start()
        else:
            self.stop()

    def stop(self):
        print(f"Stop Discovery", flush=True)
        self.stop_checking()
        self.networkcb.stop()
        self.cached_peers = []
        if self.beacon:
            self.beacon.close()
        if self.pipe:
            self.pipe.close()
        if self.requestpipe:
            self.requestpipe.close()
        if self.agent:
            self.agent.stop()
            self.agent = None
        if self.ctx:
            self.ctx.destroy()
        # self.ctx.term()

    def start(self):
        print(f"Start Discovery here", flush=True)
        self.beacon.run()
        if self.node.settings.discoverable == True:            
            self.make_discoverable(True)
        # if not (self.agent_thread and self.agent_thread.is_alive()):
        if not self.agent or not self.agent_thread.is_alive():
            self.ctx = zmq.Context()
            p0, p1 = pipe(self.ctx)
            p2, p3 = pipe(self.ctx)
            self.agent = InterfaceAgent(self.ctx, self.node, p1, p3)
            self.agent_thread = Thread(target=self.agent.start)
            self.agent_thread.start()
            self.pipe = p0
            self.requestpipe = p2
            self.nodecb.start()     
            self.networkcb.start()       
            

    def update_name(self, name):
        self.beacon.update_name(name)
        if self.node.settings.discoverable == True:
            self.beacon.update()

    def make_discoverable(self, val):
        # print(f"Make discoverable: {val}",flush=True)
        if val:
            self.beacon.register()
        else:
            self.beacon.unregister()
    
    def send(self, evt):
        self.pipe.send_multipart(evt)
        
    def recv(self):
        """receive a message from our interface"""
        return self.pipe.recv_multipart()

    def nodes(self):
        if self.node.settings.discovery == True:            
            return self.cached_peers
        else:
            return []
            # return [{"uuid": self.node.model.uuid, "name": self.node.name, "ip": self.beacon.local_ip}]
            # return [self.node.model.to_json(only = [Node.uuid, Node.name])]

    def request(self, msg):
        # print("Send request, get reply")
        # request = [b"REQUEST"] + msg
        if not self.requestpipe:
            raise AncillaError(400, {"error": "Discovery is not running"})
        self.requestpipe.send_multipart(msg)
        reply = self.requestpipe.recv_multipart()
        # print(f'Reply = {reply}', flush=True)
        kind, msg = reply
        return msg.decode('utf-8')

    def stop_checking(self):
        self.nodecb.stop()
        msg = [b'notifications.nodes_changed', b'check', b'{"nodes":"check"}']
        if hasattr(self.node, 'publisher'):
            self.node.publisher.send_multipart(msg)

    def check_nodes(self):
        res = self.request([b'peers'])
        new_peers = json.loads(res)
        if self.cached_peers != new_peers:
            # print(f"Peers are different")
            self.cached_peers = new_peers         
            msg = [b'notifications.nodes_changed', b'check', b'{"nodes":"check"}']
            self.node.publisher.send_multipart(msg)

    def check_interface_addresses(self):
        ##  uap0 interface is used by our wifi docker container to be used as a wifi access point (allow incoming connections)
        ## wlan0 interface is used as the client to connect to outside wifi
        accesspointinterface = 'uap0'
        gws = netifaces.gateways()
        interfaces = netifaces.interfaces()
        default_interface = None
        address = None
        # if netifaces.AF_INET in gws['default']:
        i = gws['default'].get(netifaces.AF_INET) or ()
        if len(i) > 1:
            default_interface = i[1]

        if default_interface:
            netaddress = netifaces.ifaddresses(default_interface).get(netifaces.AF_INET) or []
            addr = (netaddress[0] or {}).get('addr')
            if addr and not addr.startswith('127'):
                address = addr
        
        
        if not address:
            for face in interfaces:
                addrs = (netifaces.ifaddresses(face).get(netifaces.AF_INET) or [])
                for addrdict in addrs:
                    addr = addrdict.get('addr')
                    if not address and addr and not addr.startswith('127'):
                        address = addr

        if not address:
            if accesspointinterface in interfaces:
                netaddress = netifaces.ifaddresses(accesspointinterface).get(netifaces.AF_INET) or []                
                for addrdict in addrs:
                    addr = addrdict.get('addr')
                    if not address and addr and not addr.startswith('127'):
                        address = addr

                

        if not address:
            try:
                address = socket.gethostbyname_ex(socket.gethostname())[-1][0]
            except Exception as e:
                print(f"NoAddress {str(e)}")
                address = '127.0.0.1'

        return address


    def check_network(self):
        #     # print("CHECK NETWORK")
        adr = self.check_interface_addresses()
        print(f"address = {adr}")
        if self.current_address != adr:
            self.current_address = adr
            if self.current_address:
                self.beacon.address = self.current_address
                self.beacon.update_network(self.node.settings.discovery, self.node.settings.discoverable)
        # if self.agent and self.agent.udp:
        #     adr = self.agent.udp.get_address()
        #     print(f"address = {adr}")
        #     if self.current_address != adr:
        #         self.current_address = adr
        #         if self.current_address:
        #             self.beacon.update_network(self.node.settings.discovery, self.node.settings.discoverable)




# =====================================================================
# Asynchronous part, works in the background

PING_PORT_NUMBER    = 9999
PING_INTERVAL       = 1.0  # Once per second
PEER_EXPIRY         = 5.0  # Five seconds and it's gone
UUID_BYTES          = 32

class Peer(object):

    uuid = None
    name = None
    ip   = None
    expires_at = None

    def __init__(self, uuid, name, ip):
        self.uuid = uuid
        self.name = name
        self.ip = ip
        self.is_alive()

    def is_alive(self, *args):
        """Reset the peers expiry time

        Call this method whenever we get any activity from a peer.
        """
        if len(args) > 0:
            uuid, name, ip, *rest = args
            self.name = name
            self.ip = ip
        self.expires_at = time.time() + PEER_EXPIRY
    
    def to_json(self):
        return {"uuid": self.uuid, "name": self.name, "ip": self.ip}


class InterfaceAgent(object):
    """This structure holds the context for our agent so we can
    pass that around cleanly to methods that need it
    """

    ctx = None                 # ZMQ context
    pipe = None                # Pipe back to application
    udp = None                 # UDP object
    uuid = None                # Our UUID as binary blob
    peers = None               # Hash of known peers, fast lookup


    def __init__(self, ctx, node, pipe, request, loop=None):
        self.ctx = ctx
        self.node = node
        self.pipe = pipe
        self.request = request
        self.loop = loop
        # self.udp = udp
        self.udp = UDP(PING_PORT_NUMBER)
        # self.uuid = uuid.uuid4().hex.encode('utf8')
        self.uuid = self.node.model.uuid # uuid.uuid4().hex
        self.peers = {}

    def stop(self):
        self.stream.close()
        if self.reappc:
            self.reappc.stop()
        if self.pingpc:
            self.pingpc.stop()
        self.udp.close()
        self.udp = None
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
                self.loop = IOLoop()
            else:
                self.loop = IOLoop.current()

        loop = self.loop
        loop.add_handler(self.udp.handle.fileno(), self.handle_beacon, loop.READ)
        self.stream = ZMQStream(self.request, loop)
        self.stream.on_recv(self.control_message)
        self.pingpc = PeriodicCallback(self.send_ping, PING_INTERVAL * 3000, 0.1)
        self.pingpc.start()
        self.reappc = PeriodicCallback(self.reap_peers, PING_INTERVAL * 3000, 0.1)
        self.reappc.start()
        loop.start()

    def send_ping(self, *a, **kw):
        if not self.node.settings.discoverable:
            return
        try:
            # print(f'node = {self.node.identity}')
            # print(f'uuid = {self.uuid}')
            packet = json.dumps([self.uuid, self.node.name]).encode('utf-8')
            # packet = b'['+self.node.identity+ b', '+ self.uuid + b']'
            # print(f'Self node #{packet}')
            self.udp.send(packet)
            # self.udp.send(self.uuid)
        except Exception as e:
            print(f'Exception = {str(e)}')
            # self.loop.stop()

    def control_message(self, event):
        """Here we handle the different control messages from the frontend."""
        
        action, *res = event
        if action == b'peers':
            p = [p.to_json() for p in self.peers.values()]
            # print(f'peer values = {p}', flush=True)
            # list(self.peers.values())
            t = [b'peers', json.dumps(p, cls=ServiceJsonEncoder).encode('utf-8')]
            # print(f"ACTION PEERS {t}", flush=True)
            self.request.send_multipart(t)
        else:
            print("control message: %s"%event)

        
    def handle_beacon(self, fd, event):
        # uuid = self.udp.recv(UUID_BYTES)
        packet, ip = self.udp.recv(128)
        pack = packet.decode('utf-8')
        try:
            res = json.loads(pack)
            uuid = res[0]
            name = res[1]
            
            # print(f"Handle beacon {ip} {uuid}  {res}")
            if uuid in self.peers:
                
                self.peers[uuid].is_alive(*res, ip)
            else:
                print("Found peer %s, %s, %s" % (uuid, name, ip))
                self.peers[uuid] = Peer(uuid, name, ip)
                self.pipe.send_multipart([b'JOINED', uuid.encode('utf-8')])
        except Exception as e:
            print(f'handle beacon exception = {str(e)}')

    def reap_peers(self):
        now = time.time()
        for peer in list(self.peers.values()):
            if peer.expires_at < now:
                print("reaping %s" % peer.uuid, peer.expires_at, now)
                self.peers.pop(peer.uuid)
                self.pipe.send_multipart([b'LEFT', peer.uuid.encode('utf-8')])
