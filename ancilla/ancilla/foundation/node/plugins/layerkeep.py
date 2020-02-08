'''
 layerkeep.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import inspect
from ...data.models import Service
from ..node_service import NodeService
from ..response import AncillaResponse, AncillaError
from ...utils import call_maybe_yield


class PluginError(Exception):
    pass

class LayerkeepPlugin(object):
    ''' This plugin passes a layerkeep service handle to route callbacks
    that accept a `layerkeep` keyword argument. If a callback does not expect
    such a parameter, no service is passed.  '''

    name = 'layerkeep'
    api = 1

    def __init__(self, keyword="layerkeep"):
         self.keyword = keyword

    def setup(self, app):
        ''' Make sure that other installed plugins don't affect the same
            keyword argument.'''
        for other in app.plugins:
            if not isinstance(other, LayerkeepPlugin): continue
            if other.keyword == self.keyword:
                raise PluginError("Found another layerkeep plugin with "\
                "conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Override global configuration with route-specific values.
        # print(f"INSIDE LKP apply {context}", flush=True)
        if hasattr(context, "app"):
            app = context.app
        else:
            app = context
        if isinstance(app, NodeService):
            lkservice = app.layerkeep_service
        else:
            lkservice = app.settings.get('_mount.app').layerkeep_service


        # Test if the original callback accepts a 'layerkeep' keyword.
        # Ignore it if it does not need the layerkeep service.
        
        if hasattr(context, "callback"):
            origcb = context.callback
        else:
            origcb = callback
        
        # args = inspect.getargspec(context.callback)[0]
        args = inspect.getargspec(origcb)[0]
        if self.keyword not in args:
            return callback

        async def wrapper(*args, **kwargs):
            
            # lkservice = Service.select().where(Service.kind == "layerkeep").first()
            kwargs[self.keyword] = lkservice
       
            try:
                rv = await call_maybe_yield(callback, *args, **kwargs)
                # print(f"CAllback rv = {rv}", flush=True)
                
            except AncillaResponse as e:
                print(f"LK Plugin Error {str(e)}", flush=True)
                raise e
            except Exception as e:
                print(f"LKP Except = {str(e)}", flush=True)
                raise AncillaError(500, {"error": str(e)}, e)
                # raise Exception(500, "Layerkeep Error", e)
            finally:
              print("INSIDE LKP FINally")
                # db.close()
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper