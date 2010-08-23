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
Configuration options for the Shell UI.
This file specifies the structure that hue-shell.ini should follow.
See conf/hue-shell.ini to configure which shells are available.
"""
from desktop.lib.conf import Config, ConfigSection, UnspecifiedConfigSection


SHELL_TYPES = UnspecifiedConfigSection(
                           key='shelltypes',
                           each=ConfigSection(members=dict(
                               nice_name=Config(key='nice_name', required=True),
                               command=Config(key='command', required=True),
                               short_name=Config(key='short_name', required=True),
                               help_doc=Config(key='help', required=False))))
