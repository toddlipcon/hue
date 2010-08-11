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

import cStringIO
import desktop.lib.wsgiserver

"""
A mixed bag of utilties that are useful but aren't themselves terribly interesting.
"""

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

class TestIO(object):
  """
  A fake output connection for use in testing.
  """
  def __init__(self, username):
    self.val = None
    self.django_style_request = self
    self.username = username
    self.user = self

  def finish(self):
    """Dummy method to imitate the API of tornado.web.RequestHandler"""
    pass

  def write(self, item):
    """Dummy write method that stores the value for reading."""
    self.val = item

  def read(self):
    """Returns the value that was stored by the "write" """
    return self.val

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

