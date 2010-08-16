# This code is taken from tornado/compat.py from rbu/tornado on GitHub.
# The URL for the repo is http://github.com/rbu/tornado.git
# The URL for the up-to-date version of the code below is http://github.com/rbu/tornado/blob/master/tornado/compat.py
#------------------------------------------
# Copyright 2010
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import httplib
try:
    httplib.responses
except AttributeError:
    from BaseHTTPServer import BaseHTTPRequestHandler
    responses = dict()
    for code, lines in BaseHTTPRequestHandler.responses.items():
        responses[code] = lines[0]
    httplib.responses = responses
