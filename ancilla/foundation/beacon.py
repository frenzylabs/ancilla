'''
 beacon.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''

import socket
import zeroconf
import time

from zeroconf import Zeroconf, ServiceInfo, ServiceBrowser, NonUniqueNameException

    # def __init__(
    #     self,
    #     type_: str,
    #     name: str,
    #     address: Optional[Union[bytes, List[bytes]]] = None,
    #     port: Optional[int] = None,
    #     weight: int = 0,
    #     priority: int = 0,
    #     properties=b'',
    #     server: Optional[str] = None,
    #     host_ttl: int = _DNS_HOST_TTL,
    #     other_ttl: int = _DNS_OTHER_TTL,
    #     *,
    #     addresses: Optional[List[bytes]] = None
    # ) -> None:

class MyListener:
    myservices = {}
    def __init__(self, *args):
      self.myservices = {}

    def remove_service(self, zeroconf, type, name):
        print("Service %s removed" % (name,))
        nm = name.split(type)[0].rstrip(".")
        del self.myservices[nm]

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        print(f"ADD SERVICE {info}")
        addresses = [("%s" % socket.inet_ntoa(a)) for a in info.addresses]
        nm = name.split(info.type)[0].rstrip(".")
        self.myservices[f"{nm}"] = {"addresses": addresses, "port": info.port, "server": info.server.rstrip("."), "type": info.type}

    def update_record(self, zeroconf, now, record):
      print("uPDATE DNS RECORD")
      info = zeroconf.get_service_info(type, record.name)
      addresses = [("%s" % socket.inet_ntoa(a)) for a in info.addresses]
      nm = info.name.split(info.type)[0].rstrip(".")
      self.myservices[f"{nm}"] = {"addresses": addresses, "port": info.port, "server": info.server.rstrip("."), "type": info.type}
      # pass

class Beacon(object):

  def __init__(self, name="ancilla", port=5000, *args, **kwargs):
    self.conf       = Zeroconf()
    # self.conf.unregister_all_services()

    self.listener = MyListener()
    
    
    self.num        = 1    
    self.name       = "{}".format(name.capitalize())
    self.identifier = self.name
    self.type       = "_{}._tcp.local.".format(name.lower())
    self.port       = port
    self.sb = ServiceBrowser(zc=self.conf, type_=self.type,
                             listener=self.listener) 

    self.conf.wait(2000)                
    
             

    self.host_name  = socket.gethostname() 
    self.host_ip    = socket.gethostbyname(self.host_name) 


  @property
  def local_ip(self):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]
    # return socket.gethostbyname(
    #   socket.gethostname()
    # )
    
  # conf.get_service_info(ztype, "{}.{}".format(name, ztype))  
  @property
  def peers(self):
    print("INSIDE PEERS")
    _broadcast  = self.conf.get_service_info(self.type, "{}.{}".format(self.name, self.type))
    print(f"INSIDE PEERSBROD {_broadcast}")
    return self.sb.services
    if not _broadcast:
      return []

    
    _addrs      = [("%s" % socket.inet_ntoa(a)) for a in _broadcast.addresses]
    print(f"INSIDE PEERS_ADDRS {_addrs}")
    return list(
      filter(lambda a: a != self.local_ip, _addrs)
    )

  @property
  def instance_name(self):
    self.identifier = self.name
    # if len(self.peers) > 0:
    if self.num > 1:
      self.identifier = "{}-{}".format(self.name, self.num)
    

      # self.name = name
      
    # print(f"INSIDE instance_name {self.identifier}")  
    # return name
    return "{}.{}".format(self.identifier, self.type)

  @property
  def domain(self):
    return "{}.local.".format(self.identifier.lower())

  @property
  def info(self):
    print("## IP: {}  // Ssss: {}".format(self.local_ip, self.peers))
    name = self.instance_name
    _info = ServiceInfo(
      self.type,
      name,
      addresses=[socket.inet_aton(self.local_ip)],
      port=self.port,
      server=self.domain
    )

    return _info

  def register(self):
    # self.conf.register_service(self.info, allow_name_change=False)
    try:
      # self.conf.check_service(self.info, allow_name_change=False)
      self.conf.register_service(self.info, allow_name_change=False)
      print(f"RegisteService: {self.info}")
    except Exception as e:
      print("Unique Name EXception")
      self.num += 1
      self.register()

      
      
  def close(self):
    self.conf.unregister_service(self.info)
    
  def update(self):
    self.conf.update_service(self.info)
