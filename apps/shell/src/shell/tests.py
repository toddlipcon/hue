#!/usr/bin/env python
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

"""Tests for shell app."""

from nose.tools import assert_true, assert_equal

import time
import shell.utils as utils
import shell.shellmanager as shellmanager
import shell.constants as constants
import desktop.lib.tornado_utils as tornado_utils
import threading

import logging
LOG = logging.getLogger(__name__)

class IOLoopStopper(threading.Thread):
  """
  The IOLoop from Tornado runs forever, so before each time we start the
  IOLoop, we start one of these threads, so that it can stop the IOLoop
  after a few seconds or some output has been produced, whichever is earlier.
  """
  def __init__(self, output, *args, **kwargs):
    threading.Thread.__init__(self, *args, **kwargs)
    self.output = output
    self.timeout = 2 # In seconds

  def run(self):
    start = time.time()
    while self.output.read() == None:
      if time.time() - start >= self.timeout:
        break
    tornado_utils.CustomIOLoop.instance().stop()

def test_create():
  """Tests shell creation."""
  smanager = shellmanager.ShellManager.global_instance()
  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Shell create test failed")

  smanager.kill_shell("a", output.read()[constants.SHELL_ID])
  output = utils.TestIO("a")
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug("Done")

def test_output():
  """Tests output from shell."""
  smanager = shellmanager.ShellManager.global_instance()
  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Shell create failed in test_output")

  shell_id = output.read().get(constants.SHELL_ID)
  output = utils.TestIO("a")
  LOG.debug("The shell id is "+shell_id)
  smanager.output_request_received("a", "", [(shell_id, 0)], output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug(output.read())
  assert_true(shell_id in output.read())
  if shell_id in output.read():
    assert_true(constants.ALIVE in output.read()[shell_id] or
              constants.EXITED in output.read()[shell_id])

  smanager.kill_shell("a", shell_id)
  output = utils.TestIO("a")
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug("Done")

def test_input():
  """Tests writing a gibberish command into a shell and finding some output (the help)"""
  smanager = shellmanager.ShellManager.global_instance()
  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Shell create failed in test_input")

  shell_id = output.read().get(constants.SHELL_ID)
  output = utils.TestIO("a")
  smanager.output_request_received("a", "", [(shell_id, 0)], output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()

  output = utils.TestIO("a")
  smanager.command_received("a", shell_id, "asdf", output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug(output.read())
  assert_true(constants.SUCCESS in output.read(), 'Sending command failed')

  smanager.kill_shell("a", shell_id)
  output = utils.TestIO("a")
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug("Done")

def test_kill():
  """Tests shell killing"""
  smanager = shellmanager.ShellManager.global_instance()

  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "First shell create failed in test_kill")
  shell_id1 = output.read()[constants.SHELL_ID]

  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Second shell create failed in test_kill")
  shell_id2 = output.read()[constants.SHELL_ID]

  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Third shell create failed in test_kill")
  shell_id3 = output.read()[constants.SHELL_ID]

  smanager.kill_shell("a", shell_id1)
  smanager.kill_shell("a", shell_id2)
  smanager.kill_shell("a", shell_id3)

  output = utils.TestIO("a")
  smanager.output_request_received("a", "", [(shell_id1, 0),
                                             (shell_id2, 0),
                                             (shell_id3, 0)], output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  assert_true( shell_id1 in output.read() or
               shell_id2 in output.read() or
               shell_id3 in output.read())
  output = utils.TestIO("a")
  smanager.output_request_received("a", "", [(shell_id1, 0),
                                             (shell_id2, 0),
                                             (shell_id3, 0)], output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  assert_true( shell_id1 in output.read() and
               shell_id2 in output.read() and
               shell_id3 in output.read())
  assert_true(constants.NO_SHELL_EXISTS in output.read()[shell_id1] and
              constants.NO_SHELL_EXISTS in output.read()[shell_id2] and
              constants.NO_SHELL_EXISTS in output.read()[shell_id3])
  LOG.debug("Done")

def test_restore():
  """Tests shell restoration."""
  smanager = shellmanager.ShellManager.global_instance()
  output = utils.TestIO("a")
  smanager.try_create("a", "pig", output)
  assert_true(constants.SUCCESS in output.read(), "Shell create failed in test_output")

  shell_id = output.read().get(constants.SHELL_ID)
  output = utils.TestIO("a")
  smanager.output_request_received("a", "", [(shell_id, 0)], output)
  helper = IOLoopStopper(output)
  helper.start()
  tornado_utils.CustomIOLoop.instance().start()
  helper.join()
  LOG.debug(output.read())
  assert_true(shell_id in output.read())
  previous_output = output.read()[shell_id][constants.OUTPUT]
  reread_output = smanager.get_previous_output("a", shell_id)
  assert_true(constants.SUCCESS in reread_output)
  reread_output = reread_output[constants.OUTPUT]
  assert_equal(previous_output, reread_output)
  LOG.debug("Done")
