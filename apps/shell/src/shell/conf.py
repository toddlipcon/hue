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
"""Configuration options for the Shell UI"""
from desktop.lib.conf import Config

SHELL_SERVER_PORT = Config(
  key="shell_server_port",
  help="Configure the port the  long-polling server runs on",
  default=7998,
  type=int)

SHELL_TYPE = Config(
  key="shell_type",
  help="Configure the type of shell that the Hue app runs",
  default = "pig -l /dev/null") # pig -l /dev/null , flume shell , hbase shell, zkCli.sh

