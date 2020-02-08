from .dict import *
# from .dict import _hkey, _hval
# from .service_json_encoder import ServiceJsonEncoder

from .cached_property import update_wrapper, cached_property
from .random import *

import asyncio
import inspect
from types import CoroutineType


def yields(value):
    return isinstance(value, asyncio.futures.Future) or inspect.isgenerator(value) or \
           isinstance(value, CoroutineType)


async def call_maybe_yield(func, *args, **kwargs):
    rv = func(*args, **kwargs)
    if yields(rv):
        rv = await rv
    return rv


