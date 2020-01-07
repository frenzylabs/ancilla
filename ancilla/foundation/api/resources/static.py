'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler
# from ...serial  import SerialConnection
from tornado.web    import Application, RequestHandler, StaticFileHandler

from serial.tools import list_ports

from typing import (
    Dict,
    Any,
    Union,
    Optional,
    Awaitable,
    Tuple,
    List,
    Callable,
    Iterable,
    Generator,
    Type,
    cast,
    overload,
)


class StaticResource(StaticFileHandler):
  def head(self, path: str = "index.html") -> Awaitable[None]:
    return self.get(path, include_body=False)

  async def get(self, path:str, include_body: bool = True):
    path = "index.html"
    self.path = self.parse_url_path(path)

    await super().get(path, True)
    