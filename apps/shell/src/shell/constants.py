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
A file to store all the constants in one place. Most constants
are the members of JSON objects, which are stored here for
easy reference.
"""

# Parameter/JSON object member names
ALIVE = "alive"
EXITED = "exited"
OUTPUT = "output"
SUCCESS = "success"
SHELL_ID = "shellId"
COMMAND = "lineToSend"
KEY_NAME = "keyName"
NICE_NAME = "niceName"
SHELL_TYPES = "shellTypes"
SHELL_KILLED = "shellKilled"
CHUNK_ID = "chunkId"
NEXT_CHUNK_ID = "nextChunkId"
NOT_LOGGED_IN = "notLoggedIn"
NO_SHELL_EXISTS = "noShellExists"
BUFFER_EXCEEDED = "bufferExceeded"
PERIODIC_RESPONSE = "periodicResponse"
SHELL_LIMIT_REACHED = "shellLimitReached"
SHELL_CREATE_FAILED = "shellCreateFailed"
MORE_OUTPUT_AVAILABLE = "moreOutputAvailable"
NUM_PAIRS = "numPairs"

# HTTP Headers used
HUE_INSTANCE_ID = "Hue-Instance-ID"

# Required environment variables
PRESERVED_ENVIRONMENT_VARIABLES = ["JAVA_HOME", "HADOOP_HOME", "PATH", "HOME", "LC_ALL", "LANG",
              "LC_COLLATE", "LC_CTYPE", "LC_MESSAGES", "LC_MONETARY", "LC_NUMERIC", "LC_TIME", "TZ",
              "FLUME_CONF_DIR"]

# Internal constants
BROWSER_REQUEST_TIMEOUT = 55
SHELL_TIMEOUT = 600
WRITE_BUFFER_LIMIT = 10000
OS_READ_AMOUNT = 40960

# The maximum number of concurrently open shells that one user can have
# This is because each shell takes up one of the 6 connections that browsers
# can have at the same time.
MAX_SHELLS = 3
