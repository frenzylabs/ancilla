'''
 discovery.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/14/20
 Copyright 2019 FrenzyLabs, LLC.
'''



import time
import uuid
from threading import Thread

import threading

import zmq
# from zmq.eventloop.ioloop import PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop, PeriodicCallback
import asyncio

from tornado.platform.asyncio import AnyThreadEventLoopPolicy
import json

import socket
import netifaces
from functools import partial

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

class Discovery(object):
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
    # current_address = None
    broadcast = None

    def __init__(self, node):
        self._current_address = None
        self.cached_peers = [] 
        self.node = node
        self.update_beacon_timeout = None

        self.current_address, self.broadcast = self.check_interface_addresses()
        self.beacon = Beacon(self.node.name, port=self.node.api_port, address=self.current_address)
        # self.beacon.address = self.current_address

        self.networkcb = PeriodicCallback(self.check_network, PING_INTERVAL * 2000, 0.2)
        self.nodecb = PeriodicCallback(self.check_nodes, PING_INTERVAL * 4000, 0.1)
        self.run(self.node.settings.discovery)


    @property
    def current_address(self):
        if not self._current_address:
            return '127.0.0.1'
        else:
            return self._current_address

    @current_address.setter
    def current_address(self, val):
        self._current_address = val
            
    def run(self, val):
        if val:
            self.start()
        else:
            self.stop()

    def stop(self):
        print(f"Stop Discovery", flush=True)
        self.stop_checking()
        self.networkcb.stop()
        if self.update_beacon_timeout:
            self.update_beacon_timeout.cancel()
        self.cached_peers = []
        if self.beacon:
            self.beacon.close()
        print(f"Closed Beacon", flush=True)
        if self.pipe:
            self.pipe.close()
        if self.requestpipe:
            self.requestpipe.close()
        if self.agent:
            self.agent.stop()
            self.agent = None
        print(f"Closed Agent", flush=True)
        if self.ctx:
            self.ctx.destroy()

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
            self.agent = DiscoveryAgent(self.ctx, self.node, p1, p3)
            self.agent.udp.broadcast = self.broadcast
            self.agent_thread = Thread(target=self.agent.start, daemon=True)
            self.agent_thread.start()
            self.pipe = p0
            self.requestpipe = p2
            self.nodecb.start()     
            self.networkcb.start()       

    def update_port(self, port):
        if self.beacon.port != port:
            self.beacon.port = port
            if self.node.settings.discoverable == True:
                self.beacon.update()

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
        if not self.requestpipe:
            raise AncillaError(400, {"error": "Discovery is not running"})
        self.requestpipe.send_multipart(msg)
        reply = self.requestpipe.recv_multipart()
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
            self.cached_peers = new_peers         
            msg = [b'notifications.nodes_changed', b'check', b'{"nodes":"check"}']
            self.node.publisher.send_multipart(msg)

    def check_interface_addresses(self):
        ##  uap0 interface is used by our wifi docker container to be used as a wifi access point (allow incoming connections)
        ## wlan0 interface is used as the client to connect to outside wifi
        accesspointinterface = 'uap0'
        gws = netifaces.gateways()
        interfaces = netifaces.interfaces()
        # list(filter(lambda x: netifaces.AF_INET in netifaces.ifaddresses(x), interfaces))
        default_interface = None
        address = None
        broadcast = None
        used_interface = ''
        # if netifaces.AF_INET in gws['default']:
        i = gws['default'].get(netifaces.AF_INET) or ()
        if len(i) > 1:
            default_interface = i[1]

        if default_interface:
            netaddress = netifaces.ifaddresses(default_interface).get(netifaces.AF_INET) or []
            if len(netaddress) > 0:
                addrdict = (netaddress[0] or {})
                addr = addrdict.get('addr')
                if addr and not addr.startswith('127'):
                    used_interface = f'DefaultGateway {default_interface}'
                    address = addr
                    if addrdict.get('broadcast'):
                        broadcast = addrdict.get('broadcast')
        
        docker_address = None
        if not address:
            for face in interfaces:
                addrs = (netifaces.ifaddresses(face).get(netifaces.AF_INET) or [])
                for addrdict in addrs:
                    addr = addrdict.get('addr')
                    if not address and addr and not addr.startswith('127'):
                        if face.startswith('docker'):
                            docker_address = addr
                        else:
                            used_interface = face
                            address = addr
                            if addrdict.get('broadcast'):
                                broadcast = addrdict.get('broadcast')
                

        if not address:
            try:
                used_interface = 'sockethostname'
                address = socket.gethostbyname_ex(socket.gethostname())[-1][0]
            except Exception as e:
                print(f"NoAddress {str(e)}")
                address = '127.0.0.1'
        
        # print(f"Face: {used_interface} curadd= {self.current_address} address = {address}, currentbroad: {self.broadcast} bcast= {broadcast}", flush=True)
        return address, broadcast


    def check_network(self):
        # print(f"CHECK NETWORK {threading.currentThread()}", flush=True)
        adr, bcast = self.check_interface_addresses()
        self.broadcast = bcast or '255.255.255.255'
        if self.agent and self.agent.udp.broadcast != self.broadcast:
            
            print(f"broadcast change: bcast udp: {self.agent.udp.broadcast} to: {self.broadcast}", flush=True)
            self.agent.udp.broadcast = self.broadcast 
            
        if self.current_address != adr or (self.beacon and self.beacon.address != adr):
            self.current_address = adr
            if self.beacon:
                self.beacon.close()
                self.beacon = None

            self._update_timeout = time.time() + 3.0
            if self.update_beacon_timeout:
                self.update_beacon_timeout.cancel()

            self.update_beacon_timeout = IOLoop.current().add_timeout(self._update_timeout, partial(self.update_beacon, adr))


        
    def update_beacon(self, adr):
        try:
            print(f'Updating Beacon {self.current_address}, New: {adr}')
            self.beacon = Beacon(self.node.name, address=adr)
            self.beacon.update_network(self.node.settings.discovery, self.node.settings.discoverable)
            self.current_address = adr
        except Exception as e:
            print(f'BeaconUpdate Exception: {str(e)}')






# =====================================================================
# Asynchronous part, works in the background

PING_PORT_NUMBER    = 9999
PING_INTERVAL       = 1.0  # Once every 2 seconds
PEER_EXPIRY         = 11.0  # 11 seconds and it's gone
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


class DiscoveryAgent(object):
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
        self.pingpc = PeriodicCallback(self.send_ping, PING_INTERVAL * 4000, 0.1)
        self.pingpc.start()
        self.reappc = PeriodicCallback(self.reap_peers, PING_INTERVAL * 5000, 0.1)
        self.reappc.start()
        loop.start()

    def send_ping(self, *a, **kw):
        if not self.node.settings.discoverable:
            return
        try:
            packet = json.dumps([self.uuid, self.node.name]).encode('utf-8')
            self.udp.send(packet)
        except Exception as e:
            print(f'Ping Exception = {str(e)}')


    def control_message(self, event):
        """Here we handle the different control messages from the frontend."""
        
        action, *res = event
        if action == b'peers':
            p = [p.to_json() for p in self.peers.values()]

            t = [b'peers', json.dumps(p, cls=ServiceJsonEncoder).encode('utf-8')]
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
