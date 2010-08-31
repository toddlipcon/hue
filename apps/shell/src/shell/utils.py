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
A mixed bag of utilties that are useful but aren't themselves terribly interesting.
"""

import shell.constants as constants
import logging

LOG = logging.getLogger(__name__)

def parse_shell_pairs(connection):
  """
  Parses out and returns a list of (shell_id, offset) tuples from a descendant of RequestHandler.
  """
  shell_pairs = []
  try:
    num_pairs = int(connection.get_argument(constants.NUM_PAIRS, ""))
  except ValueError:
    return shellpairs
  for i in xrange(1, num_pairs+1):
    shell_id_i = connection.get_argument("%s%d" % (constants.SHELL_ID, i), "-1")
    offset_i = int(connection.get_argument("%s%d" % (constants.OFFSET, i), "-1"))
    shell_pairs.append((shell_id_i, offset_i))
  return shell_pairs

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

class UserMetadata(object):
  """
  A simple class to encapsulate the metadata for a user.
  """
  def __init__(self, username):
    self.num_shells = 0
    self.current_shell_id = 0
    self.username = username

  def get_next_id(self):
    """
    Return the next available ID. Successive calls to this function will yield two different IDs.
    Returns a unicode string for compatibility with Tornado.
    """
    curr_id = self.current_shell_id
    self.current_shell_id += 1
    return unicode(curr_id)

  def decrement_count(self):
    """
    Decrement the number of shells currently open for the given user.
    """
    if self.num_shells > 0:
      self.num_shells -= 1
    else:
      LOG.error("Num shells is negative for user %s" % (self.username,))

  def increment_count(self):
    """
    Increment the number of shells currently open for the given user.
    """
    self.num_shells += 1

  def get_shell_count(self):
    """
    Return the number of shells currently open for the given user.
    """
    return self.num_shells
