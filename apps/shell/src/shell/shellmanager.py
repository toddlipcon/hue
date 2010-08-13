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
This module handles I/O with shells.  Much of the functionality has been pushed down into the
Shell class itself, but all routing occurs through the ShellManager.
"""

import cStringIO
import errno
import fcntl
import logging
import os
import signal
import shell.conf
import shell.constants as constants
import subprocess
import time
import tornado.ioloop
import desktop.lib.i18n

LOG = logging.getLogger(__name__)

class TimestampedConnection(object):
  """
  A class to wrap Tornado request handlers with timestamps.
  """
  def __init__(self, handler):
    self.handler = handler
    self.time_received = time.time()

class Shell(object):
  """
  A class to encapsulate I/O with a shell subprocess.
  """

  def __init__(self, shell_command):
    subprocess_env = {}
    env = desktop.lib.i18n.make_utf8_env()
    for item in constants.PRESERVED_ENVIRONMENT_VARIABLES:
      value = env.get(item)
      if value:
        subprocess_env[item] = value
    LOG.debug("Subprocess environment is %s" % (subprocess_env,))
    p = subprocess.Popen(shell_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                           shell=True, stderr=subprocess.STDOUT, env=subprocess_env, close_fds=True)

    ifd = p.stdin.fileno()
    ofd = p.stdout.fileno()

    # Set the output file descriptor to nonblocking mode
    fd_attr = fcntl.fcntl(ofd, fcntl.F_GETFL)
    fcntl.fcntl(ofd, fcntl.F_SETFL, fd_attr | os.O_NONBLOCK)

    # Now do the same for the input file descriptor
    fd_attr = fcntl.fcntl(ifd, fcntl.F_GETFL)
    fcntl.fcntl(ifd, fcntl.F_SETFL, fd_attr | os.O_NONBLOCK)

    # State that isn't touched by any other classes.
    self._ifd = ifd
    self._ofd = ofd
    self._subprocess = p
    self._write_buffer = cStringIO.StringIO()
    self._read_buffer = cStringIO.StringIO()
    self._prompt_connections = []
    self._output_connections = []
    self._io_loop = tornado.ioloop.IOLoop.instance()
    self._output_chunk_info = []
    self._write_callback_enabled = False
    self._read_callback_enabled = False

    # State that's accessed by other classes.
    self.last_output_sent = False # Set to true when shell exits and last output has been sent
    # Set to true when any of a bunch of things happens. Once set, _handle_periodic kills the shell
    self.remove_at_next_iteration = False
    self.time_received = time.time() # Timestamp so we know when to send our keep-alive message

  def get_previous_output(self):
    """
    Called when a Hue session is restored. Returns all previous outputs.
    """
    return ( self._read_buffer.getvalue(), len(self._output_chunk_info) )


  def command_received(self, command, connection):
    """
    Called when a command is received from the client. If we have room, we add the command to the
    write buffer. Otherwise, we tell the client that there is no more room in the write buffer.
    """
    LOG.debug("Command received for shell %s : '%s'" % (self, command,))
    if len(self._write_buffer.getvalue()) >= constants.WRITE_BUFFER_LIMIT:
      LOG.debug("Write buffer too full, dropping command")
      try:
        connection.write({ constants.BUFFER_EXCEEDED : True })
        connection.finish()
      except IOError:
        pass
    else:
      LOG.debug("Write buffer has room. Adding command to end of write buffer.")
      self._append_to_write_buffer(command)
      if not self._write_callback_enabled:
        self._io_loop.add_handler(self._ifd, self._child_writable, self._io_loop.WRITE)
        self._write_callback_enabled = True
      self._prompt_connections.append(connection)

  def mark_for_cleanup(self):
    """
    Mark this shell to be destroyed at the next iteration of the global IOLoop instance.
    """
    self.remove_at_next_iteration = True

  def _write_output_from_cache(self, chunk_id, connection):
    """
    The chunk ID is one from the past, so we just fetch the necessary stuff from cache.
    """
    start_pos = self._output_chunk_info[chunk_id][0]
    end_pos = self._output_chunk_info[-1][1]
    old_pos = self._read_buffer.tell()
    bytes_to_read = end_pos - start_pos
    self._read_buffer.seek(start_pos)
    output = self._read_buffer.read(bytes_to_read)
    self._read_buffer.seek(old_pos)
    try:
      connection.write({ constants.ALIVE: True, constants.OUTPUT: output,
      constants.MORE_OUTPUT_AVAILABLE: True, constants.NEXT_CHUNK_ID: len(self._output_chunk_info)})
      connection.finish()
    except IOError:
      pass

  def output_request_received(self, chunk_id, connection):
    """
    Called when an output request is received from the client. We note the time and stick the
    connection into the appropriate instance variable.
    """
    LOG.debug("Received output request from %s" % (connection.django_style_request.user.username,))
    self.time_received = time.time()
    if chunk_id < len(self._output_chunk_info):
      self._write_output_from_cache(chunk_id, connection)
    else:
      if not self._read_callback_enabled:
        self._io_loop.add_handler(self._ofd, self._child_readable, self._io_loop.READ)
        self._read_callback_enabled = True
      self._output_connections.append(TimestampedConnection(connection))

  def handle_periodic(self):
    """
    Called every iteration of the global IOLoop by the global ShellManager. This lets us time some
    old output connections out by writing a "Keep-Alive" equivalent.
    """
    i = 0
    currtime = time.time()
    while i < len(self._output_connections):
      try:
        conn = self._output_connections[i]
        difftime = currtime - conn.time_received
        if difftime >= constants.BROWSER_REQUEST_TIMEOUT:
          try:
            try:
              conn.handler.write({ constants.PERIODIC_RESPONSE : True })
              conn.handler.finish()
            except IOError:
              pass
          finally:
            self._output_connections.pop(i)
            i -= 1
      finally:
        i += 1

  def destroy(self):
    """
    Called during iterations of _handle_periodic in the global IOLoop. Removes the appropriate
    handlers from the IOLoop, and then kills the subprocess.
    """
    if self._read_callback_enabled:
      self._io_loop.remove_handler(self._ofd)
      self._read_callback_enabled = False
    if self._write_callback_enabled:
      self._io_loop.remove_handler(self._ifd)
      self._write_callback_enabled = False

    self._write_buffer.close()
    self._read_buffer.close()

    try:
      LOG.debug("Sending SIGKILL to process with PID %d" % (self._subprocess.pid,))
      os.kill(self._subprocess.pid, signal.SIGKILL)
      # We could try figure out which exit statuses are fine and which ones are errors.
      # But that might be difficult to do since os.wait might block.
    except OSError:
      pass # This means the subprocess was already killed, which happens if the command was "quit"

    while len(self._output_connections):
      output_connection = self._output_connections.pop().handler
      try:
        output_connection.write({ constants.SHELL_KILLED : True })
        output_connection.finish()
      except IOError:
        pass

    while len(self._prompt_connections):
      prompt_connection = self._prompt_connections.pop()
      try:
        prompt_connection.write({ constants.SHELL_KILLED : True })
        prompt_connection.finish()
      except IOError:
        pass

  def _read_child_output(self):
    """
    Reads up to constants.OS_READ_AMOUNT bytes from the child subprocess's stdout. Returns a tuple
    of (output, more_available). The second parameter indicates whether more output might be
    obtained by another call to _read_child_output.
    """
    ofd = self._ofd
    try:
      next_output = os.read(ofd, constants.OS_READ_AMOUNT)
      old_pos = self._read_buffer.tell()
      self._read_buffer.write(next_output)
      self._read_buffer.seek(old_pos)
    except OSError, e: # No more output at all
      if e.errno == errno.EINTR:
        pass
      elif e.errno != errno.EAGAIN:
        format_str = "Encountered error while reading from process with PID %d : %s"
        LOG.error( format_str % (self._subprocess.pid, e))
        self.mark_for_cleanup()
    result = self._read_buffer.read()
    self._output_chunk_info.append(( old_pos, self._read_buffer.tell() ))

    more_available = len(result) >= constants.OS_READ_AMOUNT
    next_chunk_id = len(self._output_chunk_info)
    return (result, more_available, next_chunk_id)

  def _child_readable(self, fd, events):
    """
    Called by the IOLoop when the child process's output fd has data that can be read. The data is
    read out and then written back over the output connection for that client.
    """
    LOG.debug("child_readable")
    if not len(self._output_connections):
      return

    total_output, more_available, next_chunk_id = self._read_child_output()

    # If this is the last output from the shell, let's tell the JavaScript that.
    if self._subprocess.poll() == None:
      status = constants.ALIVE
    else:
      status = constants.EXITED
      self.last_output_sent = True

    try:
      while len(self._output_connections):
        output_connection = self._output_connections.pop().handler
        try:
          output_connection.write({ status: True, constants.OUTPUT: total_output,
             constants.MORE_OUTPUT_AVAILABLE: more_available, constants.NEXT_CHUNK_ID: next_chunk_id})
          output_connection.finish()
        except IOError:
          pass
    finally:
      self._io_loop.remove_handler(self._ofd)
      self._read_callback_enabled = False

  def _append_to_write_buffer(self, command):
    """
    Append the received command, with an extra newline, to the write buffer. This buffer is used
    when the child becomes readable to send commands to the child subprocess.
    """
    self._write_buffer.seek(len(self._write_buffer.getvalue()))
    self._write_buffer.write("%s\n" % (command,))
    self._write_buffer.seek(0)

  def _read_from_write_buffer(self):
    """
    Read and return the contents of the write buffer.
    """
    contents = self._write_buffer.read()
    self._write_buffer.seek(0)
    return contents

  def _advance_write_buffer(self, num_bytes):
    """
    Advance the current position in the write buffer by num_bytes bytes.
    """
    # TODO: Replace this system with a list of cStringIO objects so that
    # it's more efficient. We should do this if this seems to be copying
    # a lot of memory around.
    self._write_buffer.seek(num_bytes)
    new_value = self._write_buffer.read()
    self._write_buffer.truncate(0)
    self._write_buffer.write(new_value)
    self._write_buffer.seek(0)

  def _child_writable(self, fd, events):
    """
    Called by the global IOLoop instance when a child subprocess's input file descriptor becomes available for writing.
    This is the point at which we send the OK back to the client so that the prompt can become available in the browser window.
    """
    LOG.debug("child_writable")
    buffer_contents = self._read_from_write_buffer()
    if buffer_contents != "":
      try:
        bytes_written = os.write(fd, buffer_contents)
        self._advance_write_buffer(bytes_written)
      except OSError, e:
        if e.errno == errno.EINTR:
          return
        elif e.errno != errno.EAGAIN:
          format_str = "Encountered error while writing to process with PID %d:%s"
          LOG.error(format_str % (self._subprocess.pid, e))
          self.mark_for_cleanup()
          return
      else:
        return

    self._io_loop.remove_handler(self._ifd)
    self._write_callback_enabled = False
    # We have prompt connections to acknowledge that we can receive more stuff. Let's do that.
    while len(self._prompt_connections):
      prompt_connection = self._prompt_connections.pop()
      try:
        prompt_connection.write({ constants.SUCCESS : True })
        prompt_connection.finish()
      except IOError:
        pass

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

class ShellManager(object):
  """
  The class that manages the relationship between requests and shell subprocesses.
  """
  def __init__(self):
    self._shells = {} # The keys are (username, shell_id) tuples
    self._meta = {} # The keys here are usernames
    self._io_loop = tornado.ioloop.IOLoop.instance()
    self._periodic_callback = tornado.ioloop.PeriodicCallback(self._handle_periodic, 1000)
    self._periodic_callback.start()

  @classmethod
  def global_instance(cls):
    """
    Similar to IOLoop's instance() classmethod. This provides an easy way for all objects to have
    a reference to the same ShellManager object without having to pass around a reference to it.
    """
    if not hasattr(cls, "_global_instance"):
      cls._global_instance = cls()
    return cls._global_instance

  def _cleanup_shell(self, key):
    """
    Clean up the shell corresponding to the specified key. Calls the destroy method on the given
    shell subprocess and then changes the metadata to keep it accurate.
    """
    shell_instance = self._shells[key]
    shell_instance.destroy()
    self._shells.pop(key)
    username = key[0]
    self._meta[username].decrement_count()

  def _handle_periodic(self):
    """
    Called at every IOLoop iteration. Kills the necessary shells and responds to the outstanding
    requests which will soon time out with "keep-alive" type messages.
    """
    LOG.debug("Entering _handle_periodic")
    try:
      keys_to_pop = []
      current_time = time.time()
      for key, shell in self._shells.iteritems():
        if shell.last_output_sent or shell.remove_at_next_iteration:
          keys_to_pop.append(key)
        else:
          difftime = current_time - shell.time_received
          if difftime >= constants.SHELL_TIMEOUT:
            keys_to_pop.append(key)
          else:
            shell.handle_periodic()
      for key in keys_to_pop:
        self._cleanup_shell(key)
    finally:
      LOG.debug("Leaving _handle_periodic")

  def try_create(self, username, connection):
    """
    Attemps to create a new shell subprocess for the given user. Writes the appropriate failure or
    success response to the client.
    """
    if not username in self._meta:
      self._meta[username] = UserMetadata(username)
    user_metadata = self._meta[username]
    if user_metadata.get_shell_count() >= constants.MAX_SHELLS:
      try:
        connection.write({ constants.SHELL_LIMIT_REACHED : True })
      except IOError:
        pass
      return

    try:
      LOG.debug("Trying to create a shell for user %s" % (username,))
      shell_instance = Shell(shell.conf.SHELL_TYPE.get())
    except (OSError, ValueError), exc:
      LOG.error("Could not create shell : %s" % (exc,))
      try:
        connection.write({ constants.SHELL_CREATE_FAILED : True })
      except IOError:
        pass
      return

    LOG.debug("Shell successfully created")
    shell_id = user_metadata.get_next_id()
    user_metadata.increment_count()
    self._shells[(username, shell_id)] = shell_instance
    try:
      connection.write({ constants.SUCCESS : True, constants.SHELL_ID : shell_id })
    except IOError:
      pass

  def command_received(self, username, shell_id, command, connection):
    """
    Called when a command is received from the client. Sends the command to the appropriate
    Shell instance.
    """
    shell = self._shells.get((username, shell_id))
    if not shell:
      try:
        connection.write({ constants.NO_SHELL_EXISTS : True })
        connection.finish()
      except IOError:
        pass
      return
    shell.command_received(command, connection)

  def output_request_received(self, username, shell_id, next_chunk_id, connection):
    """
    Called when an output request is received from the client. Sends the command to the appropriate
    shell instance.
    """
    shell = self._shells.get((username, shell_id))
    if not shell:
      try:
        connection.write({ constants.NO_SHELL_EXISTS : True })
        connection.finish()
      except IOError:
        pass
      return
    shell.output_request_received(next_chunk_id, connection)

  def kill_shell(self, username, shell_id):
    """
    Called when the user closes the JFrame in Hue. Marks the appropriate shell for cleanup on the
    next IOLoop iteration.
    """
    shell = self._shells.get((username, shell_id))
    if not shell:
      LOG.debug("User %s' has no shell with ID '%s'" % (username, shell_id))
      return
    shell.mark_for_cleanup()

  def get_previous_output(self, username, shell_id):
    """
    Called when the Hue session is restored. Get the outputs that we have previously written out to
    the client as one big string.
    """
    shell = self._shells.get((username, shell_id))
    if not shell:
      return { constants.SHELL_KILLED : True}
    output, next_cid = shell.get_previous_output()
    return {constants.SUCCESS: True, constants.OUTPUT: output, constants.NEXT_CHUNK_ID: next_cid}
