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

import os
import string
from django.core.management.base import NoArgsCommand
import desktop.conf
import desktop.lib.paths

class Command(NoArgsCommand):
  """
  Exec nginx. This is a wrapper so that supervisor can control nginx.
  """
  def handle_noargs(self, **options):
    nginx_conf_template = string.Template(
    """# Licensed to Cloudera, Inc. under one
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
    
    # See http://wiki.nginx.org/NginxConfiguration for documentation.
    
    worker_processes  1; # How many processes nginx should use. Recommended: no more than 1 per CPU.
    daemon off; #Run nginx in the foreground. This makes it much easier for use with Hue.
    
    events {
      worker_connections  1024; # Threads per process
    }
    
    http {
      include       mime.types;
      default_type  application/octet-stream;
      sendfile      on;
      keepalive_timeout  65;
    
      server {
        listen       $external_port; # The external port of the Hue installation.
        server_name  localhost;
        proxy_buffers 128 512k;
        proxy_buffer_size 512k;
        proxy_set_header External-Port $$server_port; # This is so Django knows it's behind a proxy
        proxy_set_header External-Addr $$server_addr; # This is so Django knows it's behind a proxy
        proxy_set_header Remote-Addr $$remote_addr; # The address of the client
        proxy_set_header Remote-Port $$remote_port; # The port of the client
    
        # Routes all requests for URLs that start with "/shell" to Tornado.
        location /shell {
          proxy_pass   http://localhost:$tornado_port; # This should be the port the Tornado server runs on
          proxy_buffering off;                # proxy_buffering must be off for long-polling
        }
    
        # Routes anything that matches "/shell" exactly to Django
        location = /shell {
          proxy_pass   http://localhost:$django_port; # This should be the port the Django server runs on
        }
    
        # Routes anything that matches "/shell/" exactly to Django
        location = /shell/ {
          proxy_pass   http://localhost:$django_port; # This should be the port the Django server runs on
        }
    
        # Routes anything that matches "/shell/static" to Django
        location /shell/static {
          proxy_pass   http://localhost:$django_port; # This should be the port the Django server runs on
        }
    
        # Routes everything else to Django
        location / {
          proxy_pass   http://localhost:$django_port; # This should be the port the Django server runs on
        }
      }
    }
    # An explanation of the directives:
    # Nginx directives are like regular expressions in the lexical analyzer for a programming language-
    # the longest match is used, and if two different directives match a URL, the first one is used.
    # If a = is present in the directive, URLs that match the location of the directive exactly are 
    # immediately proxied to the specified port - nginx will not look at any further directives.
    
    # The first directive above sends all URLs that start with /shell to Tornado. But the second and
    # third directives refine this, because the request for /shell or /shell/ should bring up the
    # slick Hue UI, not be routed to Tornado. The fourth directive routes the requests for static parts
    # of the shell app to Django as well, since the icon, the CSS, and the JavaScript should also be
    # served up by Django. The last directive allows for all other URLs to fall through and be routed to
    # Django.
    """)
    
    result = nginx_conf_template.substitute(django_port=desktop.conf.CHERRYPY_PORT.get(), 
          tornado_port=desktop.conf.TORNADO_PORT.get(), external_port=desktop.conf.HTTP_PORT.get())
          
    
    open(desktop.lib.paths.get_build_dir("env", "conf", "nginx.conf"), "w").write(result)
    
    path_to_nginx = desktop.lib.paths.get_build_dir("env", "bin", "nginx")
    os.execl(path_to_nginx, path_to_nginx) # Need the second arg because nginx crashes when called with argc=0