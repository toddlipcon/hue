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
"""Configuration for the job submission application"""

import os.path

from desktop.lib.conf import Config
from desktop.lib import paths

JOBSUBD_HOST = Config(
  key="jobsubd_host",
  help="Host where jobsubd thrift daemon is running",
  default="localhost")

JOBSUBD_PORT = Config(
  key="jobsubd_port",
  help="Port where jobsubd thrift daemon is running",
  default=8001,
  type=int)

REMOTE_DATA_DIR = Config(
  key="remote_data_dir",
  default="/user/hue/jobsub",
  help="Location on HDFS where the jobsub examples and templates are stored.")

# Where examples and templates are stored.
LOCAL_DATA_DIR = Config(
  key="local_data_dir",
  default=os.path.join(os.path.dirname(__file__), "..", "..", "data"),
  help="Location on local FS where examples and template are stored",
  private=True
)

SAMPLE_DATA_DIR = Config(
  key="sample_data_dir",
  default=paths.get_thirdparty_root("sample_data"),
  help="Location on local FS where sample data is stored",
  private=True)

# Location of trace jar
ASPECTPATH = Config(
  key="aspect_path",
  default=os.path.join(os.path.dirname(__file__), "..", "..", "java-lib", "trace.jar"),
  help="Path to the built jobsub trace.jar",
  private=True)

# Location of aspectj weaver jar
ASPECTJWEAVER = Config(
  key="aspectj_weaver",
  default=paths.get_thirdparty_root(
    "java", "aspectj-1.6.5", "aspectjweaver.jar"),
  help="Path to aspectjweaver.jar from aspectj distribution",
  private=True)
