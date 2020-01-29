'''
 response.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 12/09/19
 Copyright 2019 FrenzyLabs, LLC.
'''

import json
from ..utils import fullpath
from ..utils.dict import HeaderDict, HeaderProperty, _hkey, _hval

STATUS_CODES = dict()
STATUS_CODES[200] = "Success" 
STATUS_CODES[201] = "Created"
STATUS_CODES[400] = "Error" 
STATUS_CODES[401] = "Unauthorized"
STATUS_CODES[418] = "I'm a teapot"  # RFC 2324
STATUS_CODES[428] = "Precondition Required"
STATUS_CODES[429] = "Too Many Requests"
STATUS_CODES[431] = "Request Header Fields Too Large"
STATUS_CODES[451] = "Unavailable For Legal Reasons" # RFC 7725
STATUS_CODES[500] = "Server Error"
STATUS_CODES[511] = "Network Authentication Required"
_STATUS_LINES = dict((k, '%d %s' % (k, v))
                          for (k, v) in STATUS_CODES.items())

class BaseResponse(object):
    """ Storage class for a response body as well as headers.

        This class does support dict-like case-insensitive item-access to
        headers, but is NOT a dict. Most notably, iterating over a response
        yields parts of the body and not the headers.

        :param body: The response body as one of the supported types.
        :param status: Either an HTTP status code (e.g. 200) or a status line
                       including the reason phrase (e.g. '200 OK').
        :param headers: A dictionary or a list of name-value pairs.

        Additional keyword arguments are added to the list of headers.
        Underscores in the header name are replaced with dashes.
    """

    default_status = 200
    default_content_type = 'application/json; charset=UTF-8'

    # Header blacklist for specific response codes
    # (rfc2616 section 10.2.3 and 10.3.5)
    bad_headers = {
        204: frozenset(('Content-Type', 'Content-Length')),
        304: frozenset(('Allow', 'Content-Encoding', 'Content-Language',
                  'Content-Length', 'Content-Range', 'Content-Type',
                  'Content-Md5', 'Last-Modified'))
    }

    def __init__(self, body='', status=None, headers=None, **more_headers):
        self._headers = {}
        self.body = body
        self.status = status or self.default_status
        if headers:
            if isinstance(headers, dict):
                headers = headers.items()
            for name, value in headers:
                self.add_header(name, value)
        if more_headers:
            for name, value in more_headers.items():
                self.add_header(name, value)

    def copy(self, cls=None):
        """ Returns a copy of self. """
        cls = cls or BaseResponse
        assert issubclass(cls, BaseResponse)
        copy = cls()
        copy.status = self.status
        # copy._headers = dict((k, v[:]) for (k, v) in self._headers.items())
        return copy

    def __iter__(self):
        return iter(self.body)

    def close(self):
        if hasattr(self.body, 'close'):
            self.body.close()

    @property
    def status_line(self):
        """ The HTTP status line as a string (e.g. ``404 Not Found``)."""
        return self._status_line

    @property
    def status_code(self):
        """ The HTTP status code as an integer (e.g. 404)."""
        return self._status_code
    
    @property
    def success(self):
        """ The HTTP status code as an integer (e.g. 404)."""
        return self._status_code >= 200 and self._status_code < 300

    def _set_status(self, status):
        if isinstance(status, int):
            code, status = status, _STATUS_LINES.get(status)
        elif ' ' in status:
            status = status.strip()
            code = int(status.split()[0])
        else:
            raise ValueError('String status line without a reason phrase.')
        if not 100 <= code <= 999:
            raise ValueError('Status code out of range.')
        self._status_code = code
        self._status_line = str(status or ('%d Unknown' % code))

    def _get_status(self):
        return self._status_line

    status = property(
        _get_status, _set_status, None,
        ''' A writeable property to change the HTTP response status. It accepts
            either a numeric code (100-999) or a string with a custom reason
            phrase (e.g. "404 Brain not found"). Both :data:`status_line` and
            :data:`status_code` are updated accordingly. The return value is
            always a status string. ''')
    del _get_status, _set_status

    @property
    def headers(self):
        """ An instance of :class:`HeaderDict`, a case-insensitive dict-like
            view on the response headers. """
        hdict = HeaderDict()
        hdict.dict = self._headers
        return hdict

    # def __contains__(self, name):
    #     return _hkey(name) in self._headers

    # def __delitem__(self, name):
    #     del self._headers[_hkey(name)]

    # def __getitem__(self, name):
    #     return self._headers[_hkey(name)][-1]

    # def __setitem__(self, name, value):
    #     self._headers[_hkey(name)] = [_hval(value)]

    # def get_header(self, name, default=None):
    #     """ Return the value of a previously defined header. If there is no
    #         header with that name, return a default value. """
    #     return self._headers.get(_hkey(name), [default])[-1]

    def set_header(self, name, value):
        """ Create a new response header, replacing any previously defined
            headers with the same name. """
        self._headers[_hkey(name)] = [_hval(value)]

    def add_header(self, name, value):
        """ Add an additional response header, not removing duplicates. """
        self._headers.setdefault(_hkey(name), []).append(_hval(value))

    def iter_headers(self):
        """ Yield (header, value) tuples, skipping headers that are not
            allowed with the current response status code. """
        return self.headerlist

    @property
    def headerlist(self):
        """ WSGI conform list of (header, value) tuples. """
        out = []
        headers = list(self._headers.items())
        if 'Content-Type' not in self._headers:
            headers.append(('Content-Type', [self.default_content_type]))
        if self._status_code in self.bad_headers:
            bad_headers = self.bad_headers[self._status_code]
            headers = [h for h in headers if h[0] not in bad_headers]
        out += [(name, val) for (name, vals) in headers for val in vals]

        out = [(k, v.encode('utf8').decode('latin1')) for (k, v) in out]
        return out

    content_type = HeaderProperty('Content-Type')
    content_length = HeaderProperty('Content-Length', reader=int, default=-1)
    # expires = HeaderProperty(
    #     'Expires',
    #     reader=lambda x: datetime.utcfromtimestamp(parse_date(x)),
    #     writer=lambda x: http_date(x))

    # @property
    # def charset(self, default='UTF-8'):
    #     """ Return the charset specified in the content-type header (default: utf8). """
    #     if 'charset=' in self.content_type:
    #         return self.content_type.split('charset=')[-1].split(';')[0].strip()
    #     return default


    # def __repr__(self):
    #     out = ''
    #     for name, value in self.headerlist:
    #         out += '%s: %s\n' % (name.title(), value.strip())
    #     return out

class AncillaResponse(BaseResponse, Exception):
    def __init__(self, body='', status=None, headers=None, **more_headers):
        super(AncillaResponse, self).__init__(body, status, headers, **more_headers)
    
    def apply(self, other):
        other._status_code = self._status_code
        other._status_line = self._status_line
        other._headers = self._headers
        other.body = self.body
    
    def __str__(self):
      return self.status_line


    def encode(self, *args):
      data = {
          "body": self.body,
          "status": self.status,
          "headers": self.headerlist
      }
      return json.dumps({"__class__": fullpath(self), "data": data}).encode('ascii')

    @classmethod
    def decode(cls, data, *args):
        try:
            # content = json.loads(data)
            # d = content.get("data")
            resp = cls(**data)
            # if d.get("exception"):
            return resp
        except Exception as e:
            print("Could Not Decode Response")
            return cls(400, exception=e)

class AncillaError(AncillaResponse):
    default_status = 500

    def __init__(self,
                 status=None,
                 body=None,
                 exception=None,
                 traceback=None, **more_headers):
        self.exception = exception
        self.traceback = traceback
        super().__init__(body, status, **more_headers)        
    
    def __str__(self):      
      if self.exception:
        return f'{self.status_line}: {str(self.exception)}' 
      return f'{self.status_line}'

    def encode(self, *args):
      data = {
          "body": self.body,
          "status": self.status,
          "headers": self.headerlist
      }
      return json.dumps({"__class__": fullpath(self), "data": data}).encode('ascii')

    @classmethod
    def decode(cls, data, *args):
        try:
            # content = json.loads(data)
            # print(f"ErrClass = {cls}")
            # print(f"ErrClassData = {data}")
            d = data #content.get("data")
            # if d.get("headers", {})
            er = cls(status=d.get("status"), body=d.get("body"), headers=d.get("headers", {}))
            # if d.get("exception"):
            return er
        except Exception as e:
            print("Could Not Decode Response")
            return cls(400, exception=e)
    