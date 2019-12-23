import threading
import time
import zmq
from tornado.ioloop import IOLoop

from .response import AncillaResponse, AncillaError
from .router import Route, Router, DictProperty, lazy_attribute, RouterError, getargspec

import sys
import base64, cgi, email.utils, functools, hmac, imp, itertools, mimetypes,\
        os, re, tempfile, threading, time, warnings, weakref, hashlib

import configparser
import inspect
import asyncio
from types import CoroutineType

DEBUG = False

py3k = sys.version_info.major > 2


def makelist(data):  # This is just too handy
    if isinstance(data, (tuple, list, set, dict)):
        return list(data)
    elif data:
        return [data]
    else:
        return []

def update_wrapper(wrapper, wrapped, *a, **ka):
    try:
        functools.update_wrapper(wrapper, wrapped, *a, **ka)
    except AttributeError:
        pass        

class cached_property(object):
    """ A property that is only computed once per instance and then replaces
        itself with an ordinary attribute. Deleting the attribute resets the
        property. """

    def __init__(self, func):
        update_wrapper(self, func)
        self.func = func

    def __get__(self, obj, cls):
        if obj is None: return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value


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


_UNSET = object()

class ConfigDict(dict):
    """ A dict-like configuration storage with additional support for
        namespaces, validators, meta-data, overlays and more.

        This dict-like class is heavily optimized for read access. All read-only
        methods as well as item access should be as fast as the built-in dict.
    """

    __slots__ = ('_parent', '_meta', '_change_listener', '_overlays', '_virtual_keys', '_source', '__weakref__')

    def __init__(self):
        self._parent = None
        self._meta = {}
        self._change_listener = []
        #: Weak references of overlays that need to be kept in sync.
        self._overlays = []
        #: Config that is the source for this overlay.
        self._source = None
        #: Keys of values copied from the source (values we do not own)
        self._virtual_keys = set()

    def load_module(self, path, squash=True):
        """Load values from a Python module.

           Example modue ``config.py``::

                DEBUG = True
                SQLITE = {
                    "db": ":memory:"
                }


           >>> c = ConfigDict()
           >>> c.load_module('config')
           {DEBUG: True, 'SQLITE.DB': 'memory'}
           >>> c.load_module("config", False)
           {'DEBUG': True, 'SQLITE': {'DB': 'memory'}}

           :param squash: If true (default), dictionary values are assumed to
                          represent namespaces (see :meth:`load_dict`).
        """
        config_obj = load(path)
        obj = {key: getattr(config_obj, key) for key in dir(config_obj)
               if key.isupper()}

        if squash:
            self.load_dict(obj)
        else:
            self.update(obj)
        return self

    def load_config(self, filename, **options):
        """ Load values from an ``*.ini`` style config file.

            A configuration file consists of sections, each led by a
            ``[section]`` header, followed by key/value entries separated by
            either ``=`` or ``:``. Section names and keys are case-insensitive.
            Leading and trailing whitespace is removed from keys and values.
            Values can be omitted, in which case the key/value delimiter may
            also be left out. Values can also span multiple lines, as long as
            they are indented deeper than the first line of the value. Commands
            are prefixed by ``#`` or ``;`` and may only appear on their own on
            an otherwise empty line.

            Both section and key names may contain dots (``.``) as namespace
            separators. The actual configuration parameter name is constructed
            by joining section name and key name together and converting to
            lower case.

            The special sections ``bottle`` and ``ROOT`` refer to the root
            namespace and the ``DEFAULT`` section defines default values for all
            other sections.

            With Python 3, extended string interpolation is enabled.

            :param filename: The path of a config file, or a list of paths.
            :param options: All keyword parameters are passed to the underlying
                :class:`python:configparser.ConfigParser` constructor call.

        """
        options.setdefault('allow_no_value', True)
        if py3k:
            options.setdefault('interpolation',
                               configparser.ExtendedInterpolation())
        conf = configparser.ConfigParser(**options)
        conf.read(filename)
        for section in conf.sections():
            for key in conf.options(section):
                value = conf.get(section, key)
                if section not in ['bottle', 'ROOT']:
                    key = section + '.' + key
                self[key.lower()] = value
        return self

    def load_dict(self, source, namespace=''):
        """ Load values from a dictionary structure. Nesting can be used to
            represent namespaces.

            >>> c = ConfigDict()
            >>> c.load_dict({'some': {'namespace': {'key': 'value'} } })
            {'some.namespace.key': 'value'}
        """
        for key, value in source.items():
            if isinstance(key, str):
                nskey = (namespace + '.' + key).strip('.')
                if isinstance(value, dict):
                    self.load_dict(value, namespace=nskey)
                else:
                    self[nskey] = value
            else:
                raise TypeError('Key has type %r (not a string)' % type(key))
        return self

    def update(self, *a, **ka):
        """ If the first parameter is a string, all keys are prefixed with this
            namespace. Apart from that it works just as the usual dict.update().

            >>> c = ConfigDict()
            >>> c.update('some.namespace', key='value')
        """
        prefix = ''
        if a and isinstance(a[0], str):
            prefix = a[0].strip('.') + '.'
            a = a[1:]
        for key, value in dict(*a, **ka).items():
            self[prefix + key] = value

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
        return self[key]

    def __setitem__(self, key, value):
        # print(f"INSIDE SET ITEM {key} {value}", flush=True)
        # print(f"Parent= {self._parent}", flush=True)
        if not isinstance(key, str):
            raise TypeError('Key has type %r (not a string)' % type(key))

        
        self._virtual_keys.discard(key)

        value = self.meta_get(key, 'filter', lambda x: x)(value)
        if key in self and self[key] is value:
            return

        self._on_change(key, value)
        dict.__setitem__(self, key, value)

        for overlay in self._iter_overlays():
            overlay._set_virtual(key, value)

    def __delitem__(self, key):
        if key not in self:
            raise KeyError(key)
        if key in self._virtual_keys:
            raise KeyError("Virtual keys cannot be deleted: %s" % key)

        if self._source and key in self._source:
            # Not virtual, but present in source -> Restore virtual value
            dict.__delitem__(self, key)
            self._set_virtual(key, self._source[key])
        else:  # not virtual, not present in source. This is OUR value
            self._on_change(key, None)
            dict.__delitem__(self, key)
            for overlay in self._iter_overlays():
                overlay._delete_virtual(key)

    def _set_virtual(self, key, value):
        """ Recursively set or update virtual keys. Do nothing if non-virtual
            value is present. """
        if key in self and key not in self._virtual_keys:
            return  # Do nothing for non-virtual keys.

        self._virtual_keys.add(key)
        if key in self and self[key] is not value:
            self._on_change(key, value)
        dict.__setitem__(self, key, value)
        for overlay in self._iter_overlays():
            overlay._set_virtual(key, value)

    def _delete_virtual(self, key):
        """ Recursively delete virtual entry. Do nothing if key is not virtual.
        """
        if key not in self._virtual_keys:
            return  # Do nothing for non-virtual keys.

        if key in self:
            self._on_change(key, None)
        dict.__delitem__(self, key)
        self._virtual_keys.discard(key)
        for overlay in self._iter_overlays():
            overlay._delete_virtual(key)

    def _on_change(self, key, value):
        if self._parent:
            x = self._parent._on_change(key, value)
        for cb in self._change_listener:
            if cb(self, key, value):
                return True
        

    def _add_change_listener(self, func):        
        self._change_listener.append(func)
        return func
    
    def _remove_change_listener(self, func):
        f = next((item for item in self._change_listener if item.func == func), None)
        if f:
            self._change_listener.remove(f)
        return func

    def meta_get(self, key, metafield, default=None):
        """ Return the value of a meta field for a key. """
        return self._meta.get(key, {}).get(metafield, default)

    def meta_set(self, key, metafield, value):
        """ Set the meta field for a key to a new value. """
        self._meta.setdefault(key, {})[metafield] = value

    def meta_list(self, key):
        """ Return an iterable of meta field names defined for a key. """
        return self._meta.get(key, {}).keys()

    def _define(self, key, default=_UNSET, help=_UNSET, validate=_UNSET):
        """ (Unstable) Shortcut for plugins to define own config parameters. """
        if default is not _UNSET:
            self.setdefault(key, default)
        if help is not _UNSET:
            self.meta_set(key, 'help', help)
        if validate is not _UNSET:
            self.meta_set(key, 'validate', validate)

    def _iter_overlays(self):
        for ref in self._overlays:
            overlay = ref()
            if overlay is not None:
                yield overlay

    def _make_overlay(self):
        """ (Unstable) Create a new overlay that acts like a chained map: Values
            missing in the overlay are copied from the source map. Both maps
            share the same meta entries.

            Entries that were copied from the source are called 'virtual'. You
            can not delete virtual keys, but overwrite them, which turns them
            into non-virtual entries. Setting keys on an overlay never affects
            its source, but may affect any number of child overlays.

            Other than collections.ChainMap or most other implementations, this
            approach does not resolve missing keys on demand, but instead
            actively copies all values from the source to the overlay and keeps
            track of virtual and non-virtual keys internally. This removes any
            lookup-overhead. Read-access is as fast as a build-in dict for both
            virtual and non-virtual keys.

            Changes are propagated recursively and depth-first. A failing
            on-change handler in an overlay stops the propagation of virtual
            values and may result in an partly updated tree. Take extra care
            here and make sure that on-change handlers never fail.

            Used by Route.config
        """
        # Cleanup dead references
        self._overlays[:] = [ref for ref in self._overlays if ref() is not None]

        overlay = ConfigDict()
        overlay._meta = self._meta
        overlay._source = self
        self._overlays.append(weakref.ref(overlay))
        for key in self:
            overlay._set_virtual(key, self[key])
        return overlay

    # def __getitem__(self, key):
    #     print(f"GET ITEM {key}", flush=True)
    #     return super().__getitem__(key)

    def __getattr__(self, key):
    #   print(f"INSIDE configdict GEt attr {key}", flush=True)
      res = self.get(key)
      if isinstance(res, ConfigDict):
        print(f"Key {key} is a ConfigDict", flush=True)
        res._parent = self

      return res
    #   return 'hi'
    
    def __setattr__(self, key, value):
    #   print(f"INSIDE configdict SET attr", flush=True)
    #   print(self)
    #   print(f"{key}, {value}")
      if key in self.__slots__:
          return super().__setattr__(key, value)
      else:
        self.__setitem__(key, value)
        #   self.update(key=val)
        #   self[key] = val

    def to_json(self):
        return {k : v for (k, v) in self.items()}

    # def to_json(obj):
    #     return {key : getattr(obj, key, None) for (key, v) in obj.items()}

    
    #   res = super().__setattr__(key, val)
    #   print(res, flush=True)
    #   return res
      
    #   self[key] = val
    # #   return self[key]
    #   return self[key]
    #   inst = cls()
    #   inst.find_event(key)
    #   return inst
    # __getattr__ = dict.get
    # __setattr__ = dict.__setitem__
    # __delattr__ = dict.__delitem__


class BaseRequest(object):
    """ A wrapper for WSGI environment dictionaries that adds a lot of
        convenient access methods and properties. Most of them are read-only.

        Adding new attributes to a request actually adds them to the environ
        dictionary (as 'bottle.request.ext.<name>'). This is the recommended
        way to store and access request-specific data.
    """

    __slots__ = ('environ', )

    #: Maximum size of memory buffer for :attr:`body` in bytes.
    MEMFILE_MAX = 102400

    def __init__(self, environ=None):
        """ Wrap a WSGI environ dictionary. """
        #: The wrapped WSGI environ dictionary. This is the only real attribute.
        #: All other attributes actually are read-only properties.
        self.environ = {} if environ is None else environ
        self.environ['bottle.request'] = self

    @DictProperty('environ', 'bottle.app', read_only=True)
    def app(self):
        """ Bottle application handling this request. """
        raise RuntimeError('This request is not connected to an application.')

    @DictProperty('environ', 'bottle.route', read_only=True)
    def route(self):
        """ The bottle :class:`Route` object that matches this request. """
        raise RuntimeError('This request is not connected to a route.')

    @DictProperty('environ', 'route.url_args', read_only=True)
    def url_args(self):
        """ The arguments extracted from the URL. """
        raise RuntimeError('This request is not connected to a route.')

    # @DictProperty('environ', 'route.params', read_only=True)
    # def params(self):
    #     """ The arguments extracted from the URL. """
    #     raise RuntimeError('This request is not connected to a route.')

    @DictProperty('environ', 'params', read_only=True)
    def params(self):
        """ A :class:`FormsDict` with the combined values of :attr:`query` and
            :attr:`forms`. File uploads are stored in :attr:`files`. """
        # params = FormsDict()
        # for key, value in self.query.allitems():
        #     params[key] = value
        # for key, value in self.forms.allitems():
        #     params[key] = value
        return self.environ.get("params", {})

    @DictProperty('environ', 'files', read_only=True)
    def files(self):
        """ A :class:`FormsDict` with the combined values of :attr:`query` and
            :attr:`forms`. File uploads are stored in :attr:`files`. """
        # params = FormsDict()
        # for key, value in self.query.allitems():
        #     params[key] = value
        # for key, value in self.forms.allitems():
        #     params[key] = value
        return self.environ.get("files", {})

    # @DictProperty('environ', 'bottle.request.files', read_only=True)
    # def files(self):
    #     """ File uploads parsed from `multipart/form-data` encoded POST or PUT
    #         request body. The values are instances of :class:`FileUpload`.

    #     """
    #     files = FormsDict()
    #     files.recode_unicode = self.POST.recode_unicode
    #     for name, item in self.POST.allitems():
    #         if isinstance(item, FileUpload):
    #             files[name] = item
    #     return files
    @property
    def response(self):
        return self._response

    def set_response(self, resp):
        self._response = resp

    # @property
    # def url(self):
    #     """ The full request URI including hostname and scheme. If your app
    #         lives behind a reverse proxy or load balancer and you get confusing
    #         results, make sure that the ``X-Forwarded-Host`` header is set
    #         correctly. """
    #     return self.urlparts.geturl()

    # @DictProperty('environ', 'bottle.request.urlparts', read_only=True)
    # def urlparts(self):
    #     """ The :attr:`url` string as an :class:`urlparse.SplitResult` tuple.
    #         The tuple contains (scheme, host, path, query_string and fragment),
    #         but the fragment is always empty because it is not visible to the
    #         server. """
    #     env = self.environ
    #     http = env.get('HTTP_X_FORWARDED_PROTO') or env.get('wsgi.url_scheme', 'http')
    #     host = env.get('HTTP_X_FORWARDED_HOST') or env.get('HTTP_HOST')
    #     if not host:
    #         # HTTP 1.1 requires a Host-header. This is for HTTP/1.0 clients.
    #         host = env.get('SERVER_NAME', '127.0.0.1')
    #         port = env.get('SERVER_PORT')
    #         if port and port != ('80' if http == 'http' else '443'):
    #             host += ':' + port
    #     path = urlquote(self.fullpath)
    #     return UrlSplitResult(http, host, path, env.get('QUERY_STRING'), '')

    @property
    def method(self):
        """ The ``REQUEST_METHOD`` value as an uppercase string. """
        return self.environ.get('REQUEST_METHOD', 'GET').upper()

    # @property
    @DictProperty('environ', 'PATH')
    def path(self):
        """ The ``REQUEST_METHOD`` value as an uppercase string. """
        return self.environ.get('PATH', '')

    def copy(self):
        """ Return a new :class:`Request` with a shallow :attr:`environ` copy. """
        return Request(self.environ.copy())

    def get(self, value, default=None): return self.environ.get(value, default)
    def __getitem__(self, key): return self.environ[key]
    def __delitem__(self, key): self[key] = ""; del(self.environ[key])
    def __iter__(self): return iter(self.environ)
    def __len__(self): return len(self.environ)
    def keys(self): return self.environ.keys()
    def __setitem__(self, key, value):
        """ Change an environ value and clear all caches that depend on it. """

        if self.environ.get('bottle.request.readonly'):
            raise KeyError('The environ dictionary is read-only.')

        self.environ[key] = value
        todelete = ()

        if key == 'wsgi.input':
            todelete = ('body', 'forms', 'files', 'params', 'post', 'json')
        elif key == 'QUERY_STRING':
            todelete = ('query', 'params')
        elif key.startswith('HTTP_'):
            todelete = ('headers', 'cookies')

        for key in todelete:
            self.environ.pop('bottle.request.'+key, None)

    def __repr__(self):
        return '<%s: %s %s>' % (self.__class__.__name__, self.method, self.path)

    def __getattr__(self, name):
        """ Search in self.environ for additional user defined attributes. """
        try:
            var = self.environ['bottle.request.ext.%s'%name]
            return var.__get__(self) if hasattr(var, '__get__') else var
        except KeyError:
            raise AttributeError('Attribute %r not defined.' % name)

    def __setattr__(self, name, value):
        if name == 'environ': return object.__setattr__(self, name, value)
        self.environ['bottle.request.ext.%s'%name] = value


Request = BaseRequest

# def _local_property():
#     ls = threading.local()

#     def fget(_):
#         try:
#             return ls.var
#         except AttributeError:
#             raise RuntimeError("Request context not initialized.")

#     def fset(_, value):
#         ls.var = value

#     def fdel(_):
#         del ls.var

#     return property(fget, fset, fdel, 'Thread-local property')


# class LocalRequest(BaseRequest):
#     """ A thread-local subclass of :class:`BaseRequest` with a different
#         set of attributes for each thread. There is usually only one global
#         instance of this class (:data:`request`). If accessed during a
#         request/response cycle, this instance always refers to the *current*
#         request (even on a multithreaded server). """
#     bind = BaseRequest.__init__
#     environ = _local_property()



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

        # print(f"App= {app}", flush=True)
        
        # def check_authorization(f):
        #     def wrapper(self, *args, **kwargs):
        #         print(f'Authusername = {self.settings.get("auth.user.username")}', flush=True)
        #         print(f'Settings = {self.settings}', flush=True)
        #         if not self.settings.get("auth.user.username"):
        #         raise AncillaError(status= 401, body={"error": "Not Signed In"})
        #         return f(self, *args, **kwargs)
        #     return wrapper
        tada = self

        async def mountpoint_wrapper(request, *args, **kwargs):
            # print("INSIDE MOUNTPOINT WRAPPER", flush=True)
            # rs = AncillaResponse()
            # print(f"TAD= {tada}", flush=True)
            # print(f"RS= {rs}", flush=True)
            # print(f"App= {app}", flush=True)
            # return app({})
            # return {"success": True}
            try:
                # request.path_shift(path_depth)
                # print(f"Path dep {path_depth}", flush=True)
                request.environ["PATH"] = "/" + request.path[len(prefix):]
                # print("INSIDE MOUNTPOINT WRAPPER", flush=True)
                # print(f"PATH= {request.path}", flush=True)
                # print(f"ARGS MOUNTPOINT= {args} kwargs= {kwargs}", flush=True)
                # print(f"Request= {request.environ}", flush=True)

                rs = request.response
                # rs = AncillaResponse()
                # print(f'Response = {rs}', flush=True)
                # print(f"App= {dir(app)}", flush=True)

                # def start_response(status, headerlist, exc_info=None):
                #     if exc_info:
                #         _raise(*exc_info)
                #     rs.status = status
                #     for name, value in headerlist:
                #         rs.add_header(name, value)
                #     return rs.body.append
                
                
                body = await app(request.environ, rs)
                # print(f"BODY = {body}", flush=True)
                # print(f'ResponsHeadAFter = {rs.headerlist}', flush=True)
                if isinstance(body, AncillaResponse):
                    return body
                else:
                    rs.body = body
                    return rs
                
                # rs.body = body
                # # rs.body = itertools.chain(rs.body, body) if rs.body else body
                # return rs
            finally:
                print("mountpoint finall")
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

    # @asyncio.coroutine
    async def _handle(self, environ, rs = None):
        # path = environ['bottle.raw_path'] = environ['PATH_INFO']
        # if py3k:
        #     environ['PATH_INFO'] = path.encode('latin1').decode('utf8', 'ignore')

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
                    
                    # print(f'call route = {out}', flush=True)
                    # return out
                    # return result

                except RouterError as e:
                    print(f"RouterError = {e}", flush=True)
                    print(self.catchall)

                    if not self.catchall:
                        raise e
                    
                    re_pattern = re.compile('^(/services/(?P<service>[^/]+)/(?P<service_id>[^/]+))(?P<other>.*)$')
                    re_match = re_pattern.match(request.path)
                    # print(f"Request path = {request.path}", flush=True)
                    # print(f"Request Match = {re_match}", flush=True)
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
                    print(self.catchall)
                    raise AncillaError(400, {"error": str(e)})
                    # self.api.catchUnmountedServices
                    # print(f"rule syntax = {self.router.rule_syntax}", flush=True)
                    # matches = self.router.rule_syntax.match(request.path)
                    # print(f"Matches = {matches}", flush=True)
                    
                        # self.api.catchUnmountedServices(request, **gargs)

                    # if groupdict
                    # re_pattern = re.compile('^(/services/(?<service>)/(?<service_id>))$')
                    # re_match = re_pattern.match
                    # url_args = re_match(path).groupdict()
                    # re.match(/([^\\]))
                    # request.path.split("/")
                    # self.api.catchUnmountedServices(request, service, service_id, *args, **kwargs):
                    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.api.catchUnmountedServices)  
                    # raise e
                # except HTTPResponse as E:
                #     out = E
                #     break
                # finally:
                #     if isinstance(out, HTTPResponse):
                #         out.apply(response)
                #     try:
                #         self.trigger_hook('after_request')
                #     except HTTPResponse as E:
                #         out = E
                #         out.apply(response)
        except (KeyboardInterrupt, SystemExit, MemoryError):
            raise
        except Exception as e:
            # print(f"INSIDE OTHER EXCEPTION = {str(e)}", flush=True)
            # if not self.catchall: raise e
            raise e
            # stacktrace = format_exc()
            # environ['wsgi.errors'].write(stacktrace)
            # environ['wsgi.errors'].flush()
            # # out = HTTPError(500, "Internal Server Error", E, stacktrace)
            # out.apply(response)
        # print(f'The result = {out}', flush=True)
        # print(f"Mountapp = {self.config.get('_mount.app')}", flush=True)
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



def yields(value):
    return isinstance(value, asyncio.futures.Future) or inspect.isgenerator(value) or \
           isinstance(value, CoroutineType)

# @asyncio.coroutine
# def call_maybe_yield(func, *args, **kwargs):
#     rv = func(*args, **kwargs)
#     if yields(rv):
#         rv = yield from rv
#     return rv

async def call_maybe_yield(func, *args, **kwargs):
    rv = func(*args, **kwargs)
    if yields(rv):
        rv = await rv
    return rv