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

class Command(NoArgsCommand):
  """
  Run tornado, runserver_plus, and nginx on the ports specified in desktop.conf
  """
  def handle_noargs(self, **options):
    django_port = str(desktop.conf.CHERRYPY_PORT.get())
    path_to_hue = desktop.lib.paths.get_build_dir("env", "bin", "hue")
    
    p1 = subprocess.Popen([path_to_hue, "runserver_plus", django_port], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p2 = subprocess.Popen([path_to_hue, "runlpserver"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p3 = subprocess.Popen([path_to_hue, "nginx"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    p1_ofd = p1.stdout.fileno()
    p2_ofd = p2.stdout.fileno()
    p3_ofd = p3.stdout.fileno()
    
    fcntl.fcntl(p1_ofd, fcntl.F_SETFL, fcntl.fcntl(p1_ofd, fcntl.F_GETFL) | os.O_NONBLOCK)
    fcntl.fcntl(p2_ofd, fcntl.F_SETFL, fcntl.fcntl(p2_ofd, fcntl.F_GETFL) | os.O_NONBLOCK)
    fcntl.fcntl(p3_ofd, fcntl.F_SETFL, fcntl.fcntl(p3_ofd, fcntl.F_GETFL) | os.O_NONBLOCK)
    
    subprocess_ofds = [p1_ofd, p2_ofd, p3_ofd]
    try:
      while True:
        readable_fds, writable_fds, other_fds = select.select(subprocess_ofds, [], [])
        for item in readable_fds:
          try:
            output = os.read(item, 40960)
            if len(output.strip()): # Ignore whitespace only - not interesting
              print output, # We want to do print, not LOG.debug, because the child subprocesses
              # already did LOG.foo for all the output. And don't add newlines, since they already
              # exist in the output from the child subprocesses.
          except OSError:
            pass
    except BaseException, exc:
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
