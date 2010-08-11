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
A module that provides the handlers for the Tornado component of the shell app.
"""

import shell.constants as constants
import shell.middleware
import shell.shellmanager as shellmanager
import tornado

class KillShellHandler(shell.middleware.MiddlewareHandler):
  """
  Tells the shell manager to kill the subprocess for this shell.
  """
  def post(self):
    if self.deny_hue_access:
      try:
        self.write({constants.NOT_LOGGED_IN: True})
      except IOError:
        pass
      return
    shell_id = self.get_argument(constants.SHELL_ID, "")
    smanager = shellmanager.ShellManager.global_instance()
    smanager.kill_shell(self.django_style_request.user.username, shell_id)
    try:
      self.write("")
    except IOError:
      pass

class CreateHandler(shell.middleware.MiddlewareHandler):
  """
  Attempts to create a subprocess for the requesting user. Denies access to users who are not logged in, and communicates
  whether or not the creation of the subprocess was successful.
  """
  def post(self):
    if self.deny_hue_access:
      try:
        self.write({constants.NOT_LOGGED_IN: True})
      except IOError:
        pass
      return
    smanager = shellmanager.ShellManager.global_instance()
    smanager.try_create(self.django_style_request.user.username, self)

class ProcessCommandHandler(shell.middleware.MiddlewareHandler):
  """
  Attempts to send the the specified command to the subprocess for the requesting user. Denies access to unauthenticated users
  and handles users without shells existing for them.
  """
  @tornado.web.asynchronous
  def post(self):
    if self.deny_hue_access:
      try:
        self.write({constants.NOT_LOGGED_IN: True})
        self.finish()
      except IOError:
        pass
      return

    command = self.get_argument(constants.COMMAND, "")
    shell_id = self.get_argument(constants.SHELL_ID, "")
    sman = shellmanager.ShellManager.global_instance()
    sman.command_received(self.django_style_request.user.username, shell_id, command, self)

class RetrieveOutputHandler(shell.middleware.MiddlewareHandler):
  """
  Registers an output connection for the next available output from the subprocess for the requesting user. Denies access immediately
  to unauthenticated users and users without existing remote shells.
  """
  @tornado.web.asynchronous
  def post(self):
    if self.deny_hue_access:
      try:
        self.write({constants.NOT_LOGGED_IN: True})
        self.finish()
      except IOError:
        pass
      return

    shell_id = self.get_argument(constants.SHELL_ID, "")
    next_chunk_id = int(self.get_argument(constants.NEXT_CHUNK_ID))
    smanager = shellmanager.ShellManager.global_instance()
    username = self.django_style_request.user.username
    smanager.output_request_received(username, shell_id, next_chunk_id, self)

class RestoreShellHandler(shell.middleware.MiddlewareHandler):
  """
  Retrieves previous output for the given shell. This is done when we restore a Hue session. Denies access immediately to unauthenticated
  users and users without existing remote shells.
  """
  def post(self):
    if self.deny_hue_access:
      try:
        self.write({constants.NOT_LOGGED_IN: True})
      except IOError:
        pass
      return

    shell_id = self.get_argument(constants.SHELL_ID, "")
    smanager = shellmanager.ShellManager.global_instance()
    result = smanager.get_previous_output(self.django_style_request.user.username, shell_id)
    self.write(result)
