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
import shell.utils as utils
import shell.middleware
import shell.shellmanager as shellmanager
import tornado
import logging

LOG = logging.getLogger(__name__)

class RetrieveOutputHandler(shell.middleware.MiddlewareHandler):
  """
  Registers an output connection for the next available output from the subprocesses for the requesting user. Denies access immediately
  to unauthenticated users and users without existing remote shells.
  """
  @tornado.web.asynchronous
  def post(self):
    if self.deny_hue_access:
      utils.write(self, {constants.NOT_LOGGED_IN: True}, True)
      return

    hue_instance_id = self.request.headers.get_list(constants.HUE_INSTANCE_ID)
    if len(hue_instance_id) != 1:
      LOG.error("Hue-Instance-ID header was not properly set in request from user %s" % (username,))
      utils.write(self, "", True) # TODO: Not sure what to do in this case.
      return

    hue_instance_id = hue_instance_id[0]
    username = self.django_style_request.user.username
    smanager = shellmanager.ShellManager.global_instance()
    shell_pairs = utils.parse_shell_pairs(self)
    smanager.output_request_received(username, hue_instance_id, shell_pairs, self)

class AddToOutputHandler(shell.middleware.MiddlewareHandler):
  """
  Adds the shell_id passed in to the shared output connection for the given Hue client.
  """
  def post(self):
    if self.deny_hue_access:
      utils.write(self, { constants.NOT_LOGGED_IN: True })
      return

    hue_instance_id = self.request.headers.get_list(constants.HUE_INSTANCE_ID)
    if len(hue_instance_id) != 1:
      LOG.error("Hue-Instance-ID header was not properly set in request from user %s" % (username,))
      utils.write(self, "") # TODO: Not sure what to do in this case.
      return

    hue_instance_id = hue_instance_id[0]
    username = self.django_style_request.user.username
    smanager = shellmanager.ShellManager.global_instance()
    shell_pairs = utils.parse_shell_pairs(self)
    smanager.add_to_output(username, hue_instance_id, shell_pairs, self)

class GetShellTypesHandler(shell.middleware.MiddlewareHandler):
  """
  Returns a JS object enumerating the types of shells available on the server.
  """
  def get(self):
    if self.deny_hue_access:
      utils.write(self, { constants.NOT_LOGGED_IN: True })
      return

    username = self.django_style_request.user.username
    shellmanager.ShellManager.global_instance().handle_shell_types_request(username, self)

class KillShellHandler(shell.middleware.MiddlewareHandler):
  """
  Tells the shell manager to kill the subprocess for this shell.
  """
  def post(self):
    if self.deny_hue_access:
      utils.write(self, { constants.NOT_LOGGED_IN: True })
      return

    shell_id = self.get_argument(constants.SHELL_ID, "")
    smanager = shellmanager.ShellManager.global_instance()
    smanager.kill_shell(self.django_style_request.user.username, shell_id)
    utils.write(self, "")

class CreateHandler(shell.middleware.MiddlewareHandler):
  """
  Attempts to create a subprocess for the requesting user. Denies access to users who are not logged
  in, and communicates whether or not the creation of the subprocess was successful.
  """
  def post(self):
    if self.deny_hue_access:
      utils.write(self, { constants.NOT_LOGGED_IN: True })
      return

    smanager = shellmanager.ShellManager.global_instance()
    key_name = self.get_argument(constants.KEY_NAME, "") # The key_name specifies what type of shell
    smanager.try_create(self.django_style_request.user.username, key_name, self)

class ProcessCommandHandler(shell.middleware.MiddlewareHandler):
  """
  Attempts to send the the specified command to the subprocess for the requesting user. Denies
  access to unauthenticated users and handles users without shells existing for them.
  """
  @tornado.web.asynchronous
  def post(self):
    if self.deny_hue_access:
      utils.write(self, {constants.NOT_LOGGED_IN: True}, True)
      return

    command = self.get_argument(constants.COMMAND, "")
    shell_id = self.get_argument(constants.SHELL_ID, "")
    smanager = shellmanager.ShellManager.global_instance()
    smanager.command_received(self.django_style_request.user.username, shell_id, command, self)

class RestoreShellHandler(shell.middleware.MiddlewareHandler):
  """
  Retrieves previous output for the given shell. This is done when we restore a Hue session. Denies access immediately to unauthenticated
  users and users without existing remote shells.
  """
  def post(self):
    if self.deny_hue_access:
      utils.write(self, {constants.NOT_LOGGED_IN: True})
      return

    shell_id = self.get_argument(constants.SHELL_ID, "")
    smanager = shellmanager.ShellManager.global_instance()
    result = smanager.get_previous_output(self.django_style_request.user.username, shell_id)
    utils.write(self, result)
