# Licensed to Cloudera, Inc. under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  Cloudera, Inc. licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import desktop.lib.wsgiserver
import django.core.handlers.base
import django.core.handlers.wsgi
import django.core.urlresolvers
import tornado.web
import tornado.ioloop
import logging
import cStringIO

LOG = logging.getLogger(__name__)

"""
A mixed bag of utilities that make writing long-polling and real-time Tornado
components for Hue much easier.  You'll want to use write, MiddlewareHandler,
and CustomIOLoopGenerator the most. The others are here because they are needed
for MiddlewareHandler.
"""

def write(connection, response, finish=False):
  """
  We do a ton of writing over pipes (not surprisingly) so pulling this out into a utility function
  here saves a lot of code repeat.
  """
  try:
    connection.write(response)
    if finish:
      connection.finish()
  except IOError, exc:
    LOG.error("Could not write over output pipe: %s" % (exc,))

class CustomIOLoop(object):
  """
  A factory to create 1 globally available IOLoop with the specified type of internal polling
  mechanism (e.g select, poll, kqueue, or epoll).
  """
  @classmethod
  def instance(cls, arg=None):
    if not hasattr(cls, "_instances"):
      cls._instances = {}
    if arg:
      key = type(arg)
    else:
      key = tornado.ioloop._Select
    if not key in cls._instances:
      if arg:
        arg_to_use = arg
      else:
        arg_to_use = tornado.ioloop._Select()
      cls._instances[key] = tornado.ioloop.IOLoop(arg_to_use)
    return cls._instances[key]

class FakeBaseHandler(django.core.handlers.base.BaseHandler):
  """
  A utility class that inherits from django.core.handlers.base.BaseHandler. It
  allows us to import the Django middleware and selectively apply only the
  request and view middlewares (applied before the view function). This provides
  an easy way to perform authentication using the standard Django middleware
  from a third-party application.
  """
  def __init__(self):
    super(FakeBaseHandler, self).__init__()
    if not hasattr(FakeBaseHandler, "resolver"):
      FakeBaseHandler.resolver = django.core.urlresolvers.RegexURLResolver(r'^/', "desktop.routing")

  def apply_pre_view_middleware(self, request):
    """
    Applies all the request and view middlewares. If any of them return a response, returns that.
    Otherwise returns None.
    """
    self.load_middleware()

    # Apply request middleware
    for middleware_method in self._request_middleware:
      response = middleware_method(request)
      if response:
        return response
    try:
      callback, callback_args, callback_kwargs = FakeBaseHandler.resolver.resolve(request.path_info)

      # Apply view middleware
      for middleware_method in self._view_middleware:
        response = middleware_method(request, callback, callback_args, callback_kwargs)
        if response:
          return response
    except Exception, e: # Basically a bare except, because I have no clue about middleware errors
      LOG.error("Middleware raised exception : %s" % (e))
    return None

class MiddlewareHandler(tornado.web.RequestHandler):
  """
  Our custom subclass of tornado.web.RequestHandler. By implementing the prepare() method here and
  subclassing this for all of our Tornado handlers, we can hook into our Django middleware.
  """
  def get_django_httprequest(self):
    """
    Returns a django.http.HttpRequest object constructed from the same raw HTTP as this object.
    We need this because Tornado's HTTPRequest is not compliant with Django's, which will break
    the middleware.
    """

    remote_addr = self.request.headers.get("Remote-Addr")
    remote_port = self.request.headers.get("Remote-Port")
    if remote_port:
      remote_port = int(remote_port)
    wsgi_env = FakeHTTPRequest(self.request.connection.data, remote_addr, remote_port).environ
    request = django.core.handlers.wsgi.WSGIRequest(wsgi_env)
    return request

  def apply_pre_view_middleware(self, request):
    """
    Applies the process_request and process_view middlewares to the request.
    """
    return FakeBaseHandler().apply_pre_view_middleware(request)

  # TODO: Figure out how to do the process_response(s). Not sure if this is ever going to be
  # necessary, though, so passing for now.
  def prepare(self):
    """
    The hook into the Django and Hue middleware. If the request fails authentication, we set the
    self.deny_hue_access variable to True.
    Otherwise, we set self.deny_hue_access to False.
    Subclasses are responsible for starting every request handling method with:
      if self.deny_hue_access:
        tornado_utils.write(self, {constants.NOT_LOGGED_IN: True})
    for synchronous requests.
    and
      if self.deny_hue_access:
        tornado_utils.write(self, {constants.NOT_LOGGED_IN: True}, True)
    for asynchronous requests.
    """
    request = self.get_django_httprequest()
    self.django_style_request = request
    deny_access = self.apply_pre_view_middleware(request)
    self.deny_hue_access = deny_access is not None

class FakeHTTPRequest(desktop.lib.wsgiserver.HTTPRequest):
  """
  A utility class that inherits from wsgiserver.HTTPRequest and provides a
  getter that we can use to access the WSGI-style environment dictionary.
  This gives us a way to construct a WSGI-style environment dictionary
  from a raw HTTP string.
  """
  def __init__(self, data, remote_addr, remote_port):
    self.remote_addr = remote_addr
    self.remote_port = remote_port
    self.rfile = CustomStringIO(data)
    self.wfile = cStringIO.StringIO() # for error messages
    self.environ = {}
    # We need this for parse_request to work
    self.environ["ACTUAL_SERVER_PROTOCOL"] = "HTTP/1.1"
    # We need this for the middlewares to work
    self.environ["wsgi.input"] = self.rfile
    self.wsgi_app = None
    self.ready = False
    self.started_response = False
    self.status = ""
    self.outheaders = []
    self.sent_headers = False
    self.close_connection = False
    self.chunked_write = False
    self.parse_request()
    # Now that parse_request has returned we can remove this key/value pair
    self.environ.pop("ACTUAL_SERVER_PROTOCOL")

class CustomStringIO(object):
  """
  A utility class that wraps around cStringIO.StringIO. The code path that parse_request goes down
  requires the readfile to have "maxlen" and "bytes_read" properties. So, we provide them here.
  That is the only custom thing about this class.
  """
  def __init__(self, string=None):
    self.__dict__["maxlen"] = None
    self.__dict__["bytes_read"] = None
    if string:
      self.__dict__["c_str_instance"] = cStringIO.StringIO(string)
    else:
      self.__dict__["c_str_instance"] = cStringIO.StringIO()

  def __getattr__(self, name):
    if name in ["maxlen", "bytes_read"]:
      return self.__dict__[name]
    else:
      return getattr(self.__dict__["c_str_instance"], name)

  def __setattr__(self, name, value):
    if name in ["maxlen", "bytes_read"]:
      self.__dict__[name] = value
    else:
      setattr(self.__dict__["c_str_instance"], name, value)
