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

"""
A module that provides routing information for the Tornado component of this app. The webapp_params
and urlpatterns variables below should be kept in sync. The urlpatterns can contain dummy callbacks
but the webapp_params should be legitimate. This module is used by FakeBaseHandler and by Tornado.
"""


from django.http import Http404
from django.conf.urls.defaults import patterns, url
import shell.asynchandlers as asynchandlers

def create(request):
  """
  A dummy for /shell/create.
  """
  raise Http404()

def retrieve_output(request):
  """
  A dummy for /shell/retrieve_output.
  """
  raise Http404()

def process_command(request):
  """
  A dummy for /shell/process_command.
  """
  raise Http404()

def kill_shell(request):
  """
  A dummy for /shell/kill_shell.
  """
  raise Http404()

def restore_shell(request):
  """
  A dummy for /shell/restore_shell.
  """
  raise Http404()

def get_shell_types(request):
  """
  A dummy for /shell/get_shell_types.
  """
  raise Http404()

def add_to_output(request):
  """
  A dummy for /shell/add_to_output.
  """
  raise Http404()

# This urlpatterns is totally fake: we use it to be able to use our standard
# django middleware on long-polling requests. For each URL in webapp_params,
# we should have the same URL (with an extra ^ prefixed) in urlpatterns, and
# the callback function can be a dummy that just raises Http404 and is defined above.
# This is okay since this urlpatterns is not read by django (urls.py is read instead).
urlpatterns = patterns('',
  url(r'^/?shell/create/?$',create),
  url(r'^/?shell/retrieve_output/?$', retrieve_output),
  url(r'^/?shell/process_command/?$', process_command),
  url(r'^/?shell/kill_shell/?$', kill_shell),
  url(r'^/?shell/restore_shell/?$', restore_shell),
  url(r'^/?shell/get_shell_types/?$', get_shell_types),
  url(r'^/?shell/add_to_output/?$', add_to_output),
)

# This is used by the tornado server to figure out which handler should process
# any particular request. This should be updated and then urlpatterns above should
# be kept in sync.
webapp_params = [
  (r'/shell/create/?$', asynchandlers.CreateHandler),
  (r'/shell/retrieve_output/?$', asynchandlers.RetrieveOutputHandler),
  (r'/shell/process_command/?$', asynchandlers.ProcessCommandHandler),
  (r'/shell/kill_shell/?$', asynchandlers.KillShellHandler),
  (r'/shell/restore_shell/?$', asynchandlers.RestoreShellHandler),
  (r'/shell/get_shell_types/?$', asynchandlers.GetShellTypesHandler),
  (r'/shell/add_to_output/?$', asynchandlers.AddToOutputHandler),
]
