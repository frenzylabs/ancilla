from .dict import *
from .dict import _hkey, _hval
# from .service_json_encoder import ServiceJsonEncoder

import asyncio
import inspect
from types import CoroutineType

def fullpath(o):
  module = o.__class__.__module__
  if module is None or module == str.__class__.__module__:
    return o.__class__.__name__  # Avoid reporting __builtin__
  else:
    return module + '.' + o.__class__.__name__


def yields(value):
    return isinstance(value, asyncio.futures.Future) or inspect.isgenerator(value) or \
           isinstance(value, CoroutineType)
