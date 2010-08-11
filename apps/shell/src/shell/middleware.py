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

"""A module that provides a way to integrate our Django middleware into the Tornado handlers.
Tornado handlers should subclass the MiddlewareHandler class provided here."""

import django.core.handlers.base
import django.core.handlers.wsgi
import django.core.urlresolvers
import shell.utils as utils
import tornado.web
import logging

LOG = logging.getLogger(__name__)

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
      FakeBaseHandler.resolver = django.core.urlresolvers.RegexURLResolver(r'^/', "shell.routing")

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
    Returns a django.http.HttpRequest object constructed from the same raw HTTP as this object itself.
    We need this because Tornado's HTTPRequest is not compliant with Django's, which will break
    the middleware.
    """
    remote_addr = self.request.headers.get("Remote-Addr")
    remote_port = int(self.request.headers.get("Remote-Port"))
    wsgi_env = utils.FakeHTTPRequest(self.request.connection.data, remote_addr, remote_port).environ
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
        try:
          self.write({constants.NOT_LOGGED_IN: True})
          # self.finish() # This is only if the method is decorated with @tornado.web.asynchronous
        except IOError:
          pass
    """
    request = self.get_django_httprequest()
    self.django_style_request = request
    deny_access = self.apply_pre_view_middleware(request)
    self.deny_hue_access = deny_access is not None
