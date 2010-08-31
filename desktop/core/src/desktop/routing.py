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
A module that provides routing information for the Tornado components of Hue. The webapp_params
and urlpatterns variables below should be kept in sync. The urlpatterns can contain dummy callbacks
but the webapp_params should be legitimate. This module is used by FakeBaseHandler and by Tornado.
"""
from django.http import Http404
from django.conf.urls.defaults import patterns, url
import shell.asynchandlers

def dummy(request):
  """
  A dummy function so that each urlpattern below can have something
  for the second parameter.
  """
  raise Http404()

# This urlpatterns is totally fake: we use it to be able to use our standard
# django middleware on long-polling requests. For each URL in webapp_params,
# we should have the same URL (with an extra ^ prefixed) in urlpatterns, and
# the callback function can be the dummy that just raises Http404 and is defined above.
# This is okay since this urlpatterns is not read by django (urls.py is read instead).
urlpatterns = patterns('',
  url(r'^/?shell/create/?$',dummy),
  url(r'^/?shell/retrieve_output/?$', dummy),
  url(r'^/?shell/process_command/?$', dummy),
  url(r'^/?shell/kill_shell/?$', dummy),
  url(r'^/?shell/restore_shell/?$', dummy),
  url(r'^/?shell/get_shell_types/?$', dummy),
  url(r'^/?shell/add_to_output/?$', dummy),
)

webapp_params = [
  (r'/shell/create/?$', shell.asynchandlers.CreateHandler),
  (r'/shell/retrieve_output/?$', shell.asynchandlers.RetrieveOutputHandler),
  (r'/shell/process_command/?$', shell.asynchandlers.ProcessCommandHandler),
  (r'/shell/kill_shell/?$', shell.asynchandlers.KillShellHandler),
  (r'/shell/restore_shell/?$', shell.asynchandlers.RestoreShellHandler),
  (r'/shell/get_shell_types/?$', shell.asynchandlers.GetShellTypesHandler),
  (r'/shell/add_to_output/?$', shell.asynchandlers.AddToOutputHandler),
]
