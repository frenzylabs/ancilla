import inspect
from ...data.models import Service
from ..service import NodeService
from ..response import AncillaResponse, AncillaError
from ..app import call_maybe_yield


class PluginError(Exception):
    pass

class LayerkeepPlugin(object):
    ''' This plugin passes an sqlite3 database handle to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made. You can override the database
    settings on a per-route basis. '''

    name = 'layerkeep'
    api = 1

    def __init__(self, keyword="layerkeep"):
        #  self.dbfile = dbfile
        #  self.autocommit = autocommit
        #  self.dictrows = dictrows
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
        print(f"INSIDE LKP apply {context}", flush=True)
        print(f"LKP app {context.app}", flush=True)
        print(f"LKP settings {context.app.settings}", flush=True)
        if isinstance(context.app, NodeService):
            lkservice = context.app.layerkeep_service
        else:
            lkservice = context.app.settings.get('_mount.app').layerkeep_service

        print(f"LKP service {lkservice}", flush=True)
        # settins = context.app.settings.get('layerkeep.name')
        # conf = context.config.get('sqlite') or {}
        # dbfile = conf.get('dbfile', self.dbfile)
        # autocommit = conf.get('autocommit', self.autocommit)
        # dictrows = conf.get('dictrows', self.dictrows)
        # keyword = conf.get('keyword', self.keyword)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context.callback)[0]
        if self.keyword not in args:
            return callback

        async def wrapper(*args, **kwargs):
            # Connect to the database
            # db = sqlite3.connect(dbfile)
            # This enables column access by name: row['column_name']
            # if dictrows: db.row_factory = sqlite3.Row
            # Add the connection handle as a keyword argument.
            print("INSIDE LK Wrapper", flush=True)
            
            # lkservice = Service.select().where(Service.kind == "layerkeep").first()
            kwargs[self.keyword] = lkservice

            print(f"INSIDE LK WrapperKwargs = {kwargs}", flush=True)            
            try:
                rv = await call_maybe_yield(callback, *args, **kwargs)
                print(f"CAllback rv = {rv}", flush=True)
                
            except AncillaResponse as e:
                print(f"LK Plugin Error {str(e)}", flush=True)
                raise e
            except Exception as e:
                print(f"Except = {str(e)}", flush=True)
                raise AncillaError(500, {"error": str(e)}, e)
                # raise Exception(500, "Layerkeep Error", e)
            finally:
              print("INSIDE LKP FINally")
                # db.close()
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper