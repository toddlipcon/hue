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
import shell.routing
import shell.constants
import logging

LOG = logging.getLogger(__name__)

class Command(NoArgsCommand):
  """Starts the Tornado server."""
  def handle_noargs(self, **options):
    port = desktop.conf.TORNADO_PORT.get()
    for item in shell.constants.PRESERVED_ENVIRONMENT_VARIABLES:
      if not item in os.environ:
        LOG.warn("Warning: '%s' is not set. Some apps may not run properly" % (item,))
    LOG.info("Starting long-polling server on port %d" % (port,))
    application = tornado.web.Application(shell.routing.webapp_params)
    tornado.httpserver.HTTPServer(application).listen(port)
    io_loop = tornado.ioloop.IOLoop.instance()
    try:
      io_loop.start()
    except BaseException, exc:
      LOG.error("Stopping long-polling server due to error : '%s'" % (exc,))
      io_loop.stop()
