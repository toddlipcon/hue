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

# A Template for how to add things to this config file.
#
# SHELL_<NAME HERE> = Config( # Pick some meaningful name for the shell type
#   key = "shell_<name here>" # The variable name in lowercase
#   help = "<name here> Shell" # A user-friendly version of this shell name
#   default = "<shell command here>" # The command to be run to start the shell (bc, irb, etc.)
# )
# Then you should add the all-caps variable name to the comma-separated default value for SHELL_TYPES.

SHELL_PIG = Config(
  key="shell_pig",
  help="Pig Shell (Grunt)",
  default="pig -l /dev/null"
)

SHELL_HBASE = Config(
  key="shell_hbase",
  help="HBase Shell",
  default="hbase shell"
)

SHELL_FLUME = Config(
  key="shell_flume",
  help="Flume Shell",
  default="flume shell"
)

SHELL_ZOOKEEPER = Config(
  key="shell_zookeeper",
  help="Zookeper Shell",
  default="zkCli.sh"
)

SHELL_TYPES = Config(
  key="shell_types",
  help="Comma-separated list of variable names to read from this module.",
  default="SHELL_PIG, SHELL_HBASE, SHELL_FLUME, SHELL_ZOOKEEPER"
)