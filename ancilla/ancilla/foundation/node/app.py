
import time

from .response import AncillaResponse, AncillaError
from .request import BaseRequest
from .router import Route, Router, lazy_attribute, RouterError, getargspec

from ..utils.dict import DictProperty, ConfigDict

from ..utils import makelist, cached_property, yields, call_maybe_yield

import sys
import io, base64, cgi, email.utils, functools, hmac, imp, itertools,\
        os, re, tempfile, time, warnings



DEBUG = False


def load(target, **namespace):
    """ Import a module or fetch an object from a module.

        * ``package.module`` returns `module` as a module object.
        * ``pack.mod:name`` returns the module variable `name` from `pack.mod`.
        * ``pack.mod:func()`` calls `pack.mod.func()` and returns the result.

        The last form accepts not only function calls, but any type of
        expression. Keyword arguments passed to this function are available as
        local variables. Example: ``import_string('re:compile(x)', x='[a-z]')``
    """
    module, target = target.split(":", 1) if ':' in target else (target, None)
    if module not in sys.modules: __import__(module)
    if not target: return sys.modules[module]
    if target.isalnum(): return getattr(sys.modules[module], target)
    package_name = module.split('.')[0]
    namespace[package_name] = sys.modules[package_name]
    return eval('%s.%s' % (module, target), namespace)




class WSGIFileWrapper(object):
    def __init__(self, fp, buffer_size=1024 * 64):
        self.fp, self.buffer_size = fp, buffer_size
        for attr in ('fileno', 'close', 'read', 'readlines', 'tell', 'seek'):
            if hasattr(fp, attr): setattr(self, attr, getattr(fp, attr))

    # def __iter__(self):
    #     buff, read = self.buffer_size, self.read
    #     while True:
    #         part = read(buff)
    #         if not part: return
    #         yield part

    def __aiter__(self):
        return self

    async def __anext__(self):
        data = await self.fetch_data()
        if data is not None:
            return data
        else:
            raise StopAsyncIteration

    async def fetch_data(self):
        buff, read = self.buffer_size, self.read
        part = read(buff)
        if not part: return None
        return part
        
        # return part
        # while not self.queue.empty():
        #     self.done.append(self.queue.get_nowait())
        # if not self.done:
        #     return None
        # return self.done.pop(0)


# request = LocalRequest()

def yieldroutes(func):
    """ Return a generator for routes that match the signature (name, args)
    of the func parameter. This may yield more than one route if the function
    takes optional keyword arguments. The output is best described by example::

        a()         -> '/a'
        b(x, y)     -> '/b/<x>/<y>'
        c(x, y=5)   -> '/c/<x>' and '/c/<x>/<y>'
        d(x=5, y=6) -> '/d' and '/d/<x>' and '/d/<x>/<y>'
    """
    path = '/' + func.__name__.replace('__', '/').lstrip('/')
    spec = getargspec(func)
    argc = len(spec[0]) - len(spec[3] or [])
    path += ('/<%s>' * argc) % tuple(spec[0][:argc])
    yield path
    for arg in spec[0][argc:]:
        path += '/<%s>' % arg
        yield path

def path_shift(script_name, path_info, shift=1):
    """ Shift path fragments from PATH_INFO to SCRIPT_NAME and vice versa.

        :return: The modified paths.
        :param script_name: The SCRIPT_NAME path.
        :param script_name: The PATH_INFO path.
        :param shift: The number of path fragments to shift. May be negative to
          change the shift direction. (default: 1)
    """
    if shift == 0: return script_name, path_info
    pathlist = path_info.strip('/').split('/')
    scriptlist = script_name.strip('/').split('/')
    if pathlist and pathlist[0] == '': pathlist = []
    if scriptlist and scriptlist[0] == '': scriptlist = []
    if 0 < shift <= len(pathlist):
        moved = pathlist[:shift]
        scriptlist = scriptlist + moved
        pathlist = pathlist[shift:]
    elif 0 > shift >= -len(scriptlist):
        moved = scriptlist[shift:]
        pathlist = moved + pathlist
        scriptlist = scriptlist[:shift]
    else:
        empty = 'SCRIPT_NAME' if shift < 0 else 'PATH_INFO'
        raise AssertionError("Cannot shift. Nothing left from %s" % empty)
    new_script_name = '/' + '/'.join(scriptlist)
    new_path_info = '/' + '/'.join(pathlist)
    if path_info.endswith('/') and pathlist: new_path_info += '/'
    return new_script_name, new_path_info        

class App(object):
    """ Each Bottle object represents a single, distinct web application and
        consists of routes, callbacks, plugins, resources and configuration.
        Instances are callable WSGI applications.

        :param catchall: If true (default), handle all exceptions. Turn off to
                         let debugging middleware handle exceptions.
    """

    @lazy_attribute
    def _global_config(cls):
        cfg = ConfigDict()
        cfg.meta_set('catchall', 'validate', bool)
        return cfg
    def __init__(self, *args, **kwargs):
        #: A :class:`ConfigDict` for app specific configuration.
        self.config = self._global_config._make_overlay()
        self.config._add_change_listener(
            functools.partial(self.trigger_hook, 'config'))

        self.config.update({
            "catchall": False
        })

        # if kwargs.get('catchall') is False:
        #     depr(0, 13, "Bottle(catchall) keyword argument.",
        #                 "The 'catchall' setting is now part of the app "
        #                 "configuration. Fix: `app.config['catchall'] = False`")
        #     self.config['catchall'] = False
        # if kwargs.get('autojson') is False:
        #     depr(0, 13, "Bottle(autojson) keyword argument.",
        #          "The 'autojson' setting is now part of the app "
        #          "configuration. Fix: `app.config['json.enable'] = False`")
        #     self.config['json.disable'] = True

        self._mounts = []

        #: A :class:`ResourceManager` for application files
        # self.resources = ResourceManager()

        self.routes = []  # List of installed :class:`Route` instances.
        self.router = Router()  # Maps requests to :class:`Route` instances.
        self.error_handler = {}

        # Core plugins
        self.plugins = []  # List of installed plugins.
        # self.install(JSONPlugin())
        # self.install(TemplatePlugin())

    #: If true, most exceptions are caught and returned as :exc:`HTTPError`
    catchall = DictProperty('config', 'catchall')

    __hook_names = 'before_request', 'after_request', 'app_reset', 'config'
    __hook_reversed = {'after_request'}

    @cached_property
    def _hooks(self):
        return dict((name, []) for name in self.__hook_names)

    def add_hook(self, name, func):
        """ Attach a callback to a hook. Three hooks are currently implemented:

            before_request
                Executed once before each request. The request context is
                available, but no routing has happened yet.
            after_request
                Executed once after each request regardless of its outcome.
            app_reset
                Called whenever :meth:`Bottle.reset` is called.
        """
        if name in self.__hook_reversed:
            self._hooks[name].insert(0, func)
        else:
            self._hooks[name].append(func)

    def remove_hook(self, name, func):
        """ Remove a callback from a hook. """
        if name in self._hooks and func in self._hooks[name]:
            self._hooks[name].remove(func)
            return True

    def trigger_hook(self, __name, *args, **kwargs):
        """ Trigger a hook and return a list of results. """
        # print("INSIDE TRIGGER HOOK")
        # print(f"nm: {__name} and args= {args}", flush=True)
        # print(f"hooks = {self._hooks}", flush=True)
        return [hook(*args, **kwargs) for hook in self._hooks[__name][:]]

    def hook(self, name):
        """ Return a decorator that attaches a callback to a hook. See
            :meth:`add_hook` for details."""

        def decorator(func):
            self.add_hook(name, func)
            return func

        return decorator


    def reset_app(self):
        self.router = Router()
        self.routes = []
        # self.plugins = []

    def remount_apps(self, apps):
        self._mounts = []
        for app in apps:
            self._mount_wsgi(app.config['_mount.prefix'], app)
                

    def _mount_wsgi(self, prefix, app, **options):
        segments = [p for p in prefix.split('/') if p]
        if not segments:
            raise ValueError('WSGI applications cannot be mounted to "/".')
        path_depth = len(segments)
        self._mounts.append(app)
        app.config['_mount.prefix'] = prefix
        app.config['_mount.app'] = self


        async def mountpoint_wrapper(request, *args, **kwargs):
            try:
                # request.path_shift(path_depth)
                # print(f"Path dep {path_depth}", flush=True)
                request.environ["PATH"] = "/" + request.path[len(prefix):]

                rs = request.response

                
                body = await app(request.environ, rs)
                # print(f"BODY = {body}", flush=True)
                # print(f'ResponsHeadAFter = {rs.headerlist}', flush=True)
                if isinstance(body, AncillaResponse):
                    return body
                else:
                    rs.body = body
                    return rs

            finally:
                pass
                # print("mountpoint finall")
                # request.path_shift(-path_depth)

        options.setdefault('skip', True)
        options.setdefault('method', 'PROXY')
        options.setdefault('mountpoint', {'prefix': prefix, 'target': app})
        options['callback'] = mountpoint_wrapper

        self.route('/%s/<:re:.*>' % '/'.join(segments), **options)
        # if not prefix.endswith('/'):
        #     self.route('/' + '/'.join(segments), **options)
    

    def _mount_app(self, prefix, app, **options):
        # if app in self._mounts or '_mount.app' in app.config:
        #     depr(0, 13, "Application mounted multiple times. Falling back to WSGI mount.",
        #          "Clone application before mounting to a different location.")
            

        # if options:
        #     depr(0, 13, "Unsupported mount options. Falling back to WSGI mount.",
        #          "Do not specify any route options when mounting bottle application.")
        #     return self._mount_wsgi(prefix, app, **options)

        # if not prefix.endswith("/"):
        #     depr(0, 13, "Prefix must end in '/'. Falling back to WSGI mount.",
        #          "Consider adding an explicit redirect from '/prefix' to '/prefix/' in the parent application.")
        #     return self._mount_wsgi(prefix, app, **options)

        self._mounts.append(app)
        app.config['_mount.prefix'] = prefix
        app.config['_mount.app'] = self
        for route in app.routes:
            route.rule = prefix + route.rule.lstrip('/')
            self.add_route(route)

    def mount(self, prefix, app, **options):
        """ Mount an application (:class:`Bottle` or plain WSGI) to a specific
            URL prefix. Example::

                parent_app.mount('/prefix/', child_app)

            :param prefix: path prefix or `mount-point`.
            :param app: an instance of :class:`Bottle` or a WSGI application.

            Plugins from the parent application are not applied to the routes
            of the mounted child application. If you need plugins in the child
            application, install them separately.

            While it is possible to use path wildcards within the prefix path
            (:class:`Bottle` childs only), it is highly discouraged.

            The prefix path must end with a slash. If you want to access the
            root of the child application via `/prefix` in addition to
            `/prefix/`, consider adding a route with a 307 redirect to the
            parent application.
        """

        if not prefix.startswith('/'):
            raise ValueError("Prefix must start with '/'")

        # return self._mount_app(prefix, app, **options)
        return self._mount_wsgi(prefix, app, **options)

    def merge(self, routes):
        """ Merge the routes of another :class:`Bottle` application or a list of
            :class:`Route` objects into this application. The routes keep their
            'owner', meaning that the :data:`Route.app` attribute is not
            changed. """
        if isinstance(routes, App):
            routes = routes.routes
        for route in routes:
            self.add_route(route)

    def install(self, plugin):
        """ Add a plugin to the list of plugins and prepare it for being
            applied to all routes of this application. A plugin may be a simple
            decorator or an object that implements the :class:`Plugin` API.
        """
        if hasattr(plugin, 'setup'): plugin.setup(self)
        if not callable(plugin) and not hasattr(plugin, 'apply'):
            raise TypeError("Plugins must be callable or implement .apply()")
        self.plugins.append(plugin)
        self.reset()
        return plugin

    def uninstall(self, plugin):
        """ Uninstall plugins. Pass an instance to remove a specific plugin, a type
            object to remove all plugins that match that type, a string to remove
            all plugins with a matching ``name`` attribute or ``True`` to remove all
            plugins. Return the list of removed plugins. """
        removed, remove = [], plugin
        for i, plugin in list(enumerate(self.plugins))[::-1]:
            if remove is True or remove is plugin or remove is type(plugin) \
            or getattr(plugin, 'name', True) == remove:
                removed.append(plugin)
                del self.plugins[i]
                if hasattr(plugin, 'close'): plugin.close()
        if removed: self.reset()
        return removed

    def reset(self, route=None):
        """ Reset all routes (force plugins to be re-applied) and clear all
            caches. If an ID or route object is given, only that specific route
            is affected. """
        if route is None: routes = self.routes
        elif isinstance(route, Route): routes = [route]
        else: routes = [self.routes[route]]
        for route in routes:
            route.reset()
        if DEBUG:
            for route in routes:
                route.prepare()
        self.trigger_hook('app_reset')

    def close(self):
        """ Close the application and all installed plugins. """
        for plugin in self.plugins:
            if hasattr(plugin, 'close'): plugin.close()

    # def run(self, **kwargs):
    #     """ Calls :func:`run` with the same parameters. """
    #     run(self, **kwargs)

    def match(self, environ):
        """ Search for a matching route and return a (:class:`Route` , urlargs)
            tuple. The second value is a dictionary with parameters extracted
            from the URL. Raise :exc:`HTTPError` (404/405) on a non-match."""
        return self.router.match(environ)

    # def get_url(self, routename, **kargs):
    #     """ Return a string that matches a named route """
    #     scriptname = request.environ.get('SCRIPT_NAME', '').strip('/') + '/'
    #     location = self.router.build(routename, **kargs).lstrip('/')
    #     return urljoin(urljoin('/', scriptname), location)

    def add_route(self, route):
        """ Add a route object, but do not change the :data:`Route.app`
            attribute."""
        self.routes.append(route)
        self.router.add(route.rule, route.method, route, name=route.name)
        if DEBUG: route.prepare()

    def route(self,
              path=None,
              method='GET',
              callback=None,
              name=None,
              apply=None,
              skip=None, **config):
        """ A decorator to bind a function to a request URL. Example::

                @app.route('/hello/<name>')
                def hello(name):
                    return 'Hello %s' % name

            The ``<name>`` part is a wildcard. See :class:`Router` for syntax
            details.

            :param path: Request path or a list of paths to listen to. If no
              path is specified, it is automatically generated from the
              signature of the function.
            :param method: HTTP method (`GET`, `POST`, `PUT`, ...) or a list of
              methods to listen to. (default: `GET`)
            :param callback: An optional shortcut to avoid the decorator
              syntax. ``route(..., callback=func)`` equals ``route(...)(func)``
            :param name: The name for this route. (default: None)
            :param apply: A decorator or plugin or a list of plugins. These are
              applied to the route callback in addition to installed plugins.
            :param skip: A list of plugins, plugin classes or names. Matching
              plugins are not installed to this route. ``True`` skips all.

            Any additional keyword arguments are stored as route-specific
            configuration and passed to plugins (see :meth:`Plugin.apply`).
        """
        if callable(path): path, callback = None, path
        plugins = makelist(apply)
        skiplist = makelist(skip)

        def decorator(callback):
            if isinstance(callback, str): callback = load(callback)
            for rule in makelist(path) or yieldroutes(callback):
                for verb in makelist(method):
                    verb = verb.upper()
                    route = Route(self, rule, verb, callback,
                                  name=name,
                                  plugins=plugins,
                                  skiplist=skiplist, **config)
                    self.add_route(route)
            return callback

        return decorator(callback) if callback else decorator

    def get(self, path=None, method='GET', **options):
        """ Equals :meth:`route`. """
        return self.route(path, method, **options)

    def post(self, path=None, method='POST', **options):
        """ Equals :meth:`route` with a ``POST`` method parameter. """
        return self.route(path, method, **options)

    def put(self, path=None, method='PUT', **options):
        """ Equals :meth:`route` with a ``PUT`` method parameter. """
        return self.route(path, method, **options)

    def delete(self, path=None, method='DELETE', **options):
        """ Equals :meth:`route` with a ``DELETE`` method parameter. """
        return self.route(path, method, **options)

    def patch(self, path=None, method='PATCH', **options):
        """ Equals :meth:`route` with a ``PATCH`` method parameter. """
        return self.route(path, method, **options)

    def error(self, code=500, callback=None):
        """ Register an output handler for a HTTP error code. Can
            be used as a decorator or called directly ::

                def error_handler_500(error):
                    return 'error_handler_500'

                app.error(code=500, callback=error_handler_500)

                @app.error(404)
                def error_handler_404(error):
                    return 'error_handler_404'

        """

        def decorator(callback):
            if isinstance(callback, str): callback = load(callback)
            self.error_handler[int(code)] = callback
            return callback

        return decorator(callback) if callback else decorator

    # def default_error_handler(self, res):
    #     return tob(template(ERROR_PAGE_TEMPLATE, e=res, template_settings=dict(name='__ERROR_PAGE_TEMPLATE')))

    async def _handle(self, environ, rs = None):

        environ['route.params'] = environ.get("params", {})
        environ['bottle.app'] = self
        request = BaseRequest(environ)

        if not rs:
            rs = AncillaResponse()
    
        request.set_response(rs)

        try:
            # while True: # Remove in 0.14 together with RouteReset
                out = None
                try:
                    # self.trigger_hook('before_request')
                    res = self.router.match(environ)
                    route, args = self.router.match(environ)
                    
                    # print(f"ROUTE = {route}", flush=True)
                    environ['route.handle'] = route
                    environ['bottle.route'] = route
                    environ['route.url_args'] = args
                    # print(f"Route.call = {route.call}", flush=True)
                    # result = yield from call_maybe_yield(route.call, *[request], **args)
                    out = await call_maybe_yield(route.call, *[request], **args)
                    
                    if isinstance(out, io.IOBase) and hasattr(out, 'read') and (hasattr(out, 'close') or not hasattr(out, '__aiter__')):
                        out = WSGIFileWrapper(out)


                except RouterError as e:
                    print(f"RouterError = {e}", flush=True)

                    if not self.catchall:
                        raise e
                    
                    re_pattern = re.compile('^(/api/services/(?P<service>[^/]+)/(?P<service_id>[^/]+))(?P<other>.*)$')
                    re_match = re_pattern.match(request.path)

                    if re_match:
                        gargs = re_match.groupdict()
                        # result = yield from call_maybe_yield(self.api.catchUnmountedServices, *[request], **gargs)
                        out = await call_maybe_yield(self.api.catchUnmountedServices, *[request], **gargs)
                        # return result
                    else:
                        raise e
                
                except AncillaResponse as e:
                    # print(f"INSIDE ANCilla REspone Error {str(e)}", flush=True)
                    raise e
                except Exception as e:
                    # print(f"AppCallException = {e}", flush=True)
                    raise AncillaError(400, {"error": str(e)})
                    
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception as e:
            # print(f"INSIDE OTHER EXCEPTION = {str(e)}", flush=True)
            # if not self.catchall: raise e
            raise e
            # stacktrace = format_exc()
            # environ['wsgi.errors'].write(stacktrace)
            # environ['wsgi.errors'].flush()

        if isinstance(out, AncillaResponse):
            return out
        else:
            rs.body = out
            return rs
        # return out

    
    # def _cast(self, out, peek=None):
    #     """ Try to convert the parameter into something WSGI compatible and set
    #     correct HTTP headers when possible.
    #     Support: False, str, unicode, dict, HTTPResponse, HTTPError, file-like,
    #     iterable of strings and iterable of unicodes
    #     """

    #     # Empty output is done here
    #     if not out:
    #         if 'Content-Length' not in response:
    #             response['Content-Length'] = 0
    #         return []
    #     # Join lists of byte or unicode strings. Mixed lists are NOT supported
    #     if isinstance(out, (tuple, list))\
    #     and isinstance(out[0], (bytes, unicode)):
    #         out = out[0][0:0].join(out)  # b'abc'[0:0] -> b''
    #     # Encode unicode strings
    #     if isinstance(out, unicode):
    #         out = out.encode(response.charset)
    #     # Byte Strings are just returned
    #     if isinstance(out, bytes):
    #         if 'Content-Length' not in response:
    #             response['Content-Length'] = len(out)
    #         return [out]
    #     # HTTPError or HTTPException (recursive, because they may wrap anything)
    #     # TODO: Handle these explicitly in handle() or make them iterable.
    #     if isinstance(out, HTTPError):
    #         out.apply(response)
    #         out = self.error_handler.get(out.status_code,
    #                                      self.default_error_handler)(out)
    #         return self._cast(out)
    #     if isinstance(out, HTTPResponse):
    #         out.apply(response)
    #         return self._cast(out.body)

    #     # File-like objects.
    #     if hasattr(out, 'read'):
    #         if 'wsgi.file_wrapper' in request.environ:
    #             return request.environ['wsgi.file_wrapper'](out)
    #         elif hasattr(out, 'close') or not hasattr(out, '__iter__'):
    #             return WSGIFileWrapper(out)

    #     # Handle Iterables. We peek into them to detect their inner type.
    #     try:
    #         iout = iter(out)
    #         first = next(iout)
    #         while not first:
    #             first = next(iout)
    #     except StopIteration:
    #         return self._cast('')
    #     except HTTPResponse as E:
    #         first = E
    #     except (KeyboardInterrupt, SystemExit, MemoryError):
    #         raise
    #     except Exception as error:
    #         if not self.catchall: raise
    #         first = HTTPError(500, 'Unhandled exception', error, format_exc())

    #     # These are the inner types allowed in iterator or generator objects.
    #     if isinstance(first, HTTPResponse):
    #         return self._cast(first)
    #     elif isinstance(first, bytes):
    #         new_iter = itertools.chain([first], iout)
    #     elif isinstance(first, unicode):
    #         encoder = lambda x: x.encode(response.charset)
    #         new_iter = imap(encoder, itertools.chain([first], iout))
    #     else:
    #         msg = 'Unsupported response type: %s' % type(first)
    #         return self._cast(HTTPError(500, msg))
    #     if hasattr(out, 'close'):
    #         new_iter = _closeiter(new_iter, out.close)
    #     return new_iter

    # def __call__(self, method, path, msg):
    def __call__(self, environ, rs = None):
        """ Each instance of :class:'Bottle' is a WSGI application. """
        return self._handle(environ, rs)
        # return self.wsgi(environ, start_response)

    # def __enter__(self):
    #     """ Use this application as default for all module-level shortcuts. """
    #     default_app.push(self)
    #     return self

    # def __exit__(self, exc_type, exc_value, traceback):
    #     default_app.pop()

    def __setattr__(self, name, value):
        # if name in self.__dict__:
        #     raise AttributeError("Attribute %s already defined. Plugin conflict?" % name)
        self.__dict__[name] = value


