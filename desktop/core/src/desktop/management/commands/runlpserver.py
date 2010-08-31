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
import os
import tornado.web
import tornado.ioloop
import tornado.httpserver
import desktop.settings
import desktop.lib.tornado_utils as tornado_utils
import logging

LOG = logging.getLogger(__name__)

try:
  from exceptions import BaseException
except ImportError:
  from exceptions import Exception as BaseException

class Command(NoArgsCommand):
  """Starts the Tornado server."""
  def handle_noargs(self, **options):
    port = desktop.conf.TORNADO_PORT.get()
    LOG.info("Starting long-polling server on port %d" % (port,))
    io_loop = tornado_utils.CustomIOLoop.instance()
    application = tornado.web.Application(desktop.settings.WEBAPP_PARAMS)
    tornado.httpserver.HTTPServer(application, io_loop=io_loop).listen(port)
    try:
      io_loop.start()
    except BaseException:
      LOG.debug("Stopping long-polling server...")
      io_loop.stop()
      LOG.debug("Done")
