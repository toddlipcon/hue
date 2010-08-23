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

from django.core.management.base import NoArgsCommand
import desktop.conf
import desktop.lib.paths
import logging
import subprocess
import select
import fcntl
import os
import signal

LOG = logging.getLogger(__name__)

try:
  from exceptions import BaseException
except ImportError:
  from exceptions import Exception as BaseException

class Command(NoArgsCommand):
  """
  Run tornado, runserver_plus, and nginx on the ports specified in desktop.conf
  """
  def handle_noargs(self, **options):
    django_port = str(desktop.conf.CHERRYPY_PORT.get())
    path_to_hue = desktop.lib.paths.get_build_dir("env", "bin", "hue")
    
    p1 = subprocess.Popen([path_to_hue, "runserver_plus", django_port])
    p2 = subprocess.Popen([path_to_hue, "runlpserver"])
    p3 = subprocess.Popen([path_to_hue, "nginx"])
    
    try:
      p1.wait()
      p2.wait()
      p3.wait()
    except BaseException:
      LOG.debug("Stopping servers...")
      try:
        os.kill(p1.pid, signal.SIGKILL)
      except OSError:
        pass
      try:
        os.kill(p2.pid, signal.SIGKILL)
      except OSError:
        pass
      try:
        os.kill(p3.pid, signal.SIGKILL)
      except OSError:
        pass
      LOG.debug("Done")
