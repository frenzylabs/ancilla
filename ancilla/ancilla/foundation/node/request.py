import functools
from ..utils.dict import HeaderDict, HeaderProperty, DictProperty, _hkey, _hval
from ..utils import fullpath
import json

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

    @DictProperty('environ', 'request.headers', read_only=True)
    def headers(self):
        """ A :class:`WSGIHeaderDict` that provides case-insensitive access to
            HTTP request headers. """
        # return WSGIHeaderDict(self.environ)
        hdict = HeaderDict(self.environ.get('request.headers'))
        hdict.dict = self._headers
        return hdict
    
    # @property
    # def headers(self):
    #     """ An instance of :class:`HeaderDict`, a case-insensitive dict-like
    #         view on the response headers. """
        

    def get_header(self, name, default=None):
        """ Return the value of a request header, or a given default value. """
        return self.headers.get(name, default)

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


    def encode(self, *args):
      print(f'encode request = {self.environ}')
      enviro = self.environ
      del enviro['bottle.request']

      return json.dumps({"__class__": fullpath(self), "data": {"environ": enviro}}).encode('ascii')

    def decode(self, data):
      pass


Request = BaseRequest