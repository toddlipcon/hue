#
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
#

include $(ROOT)/Makefile.vars
NGINX_DIR := nginx-0.7.67
NGINX_CONFIG := $(NGINX_DIR)/Makefile
NGINX_CONF_PARAM := --without-http_rewrite_module \
	--sbin-path=bin/nginx --prefix=$(BLD_DIR_ENV) \
	--error-log-path=$(BLD_DIR_BIN)/logs/nginx-errors.log \
	--http-log-path=$(BLD_DIR_BIN)/logs/nginx-access.log \
	--pid-path=$(BLD_DIR_BIN)/logs/nginx.pid \
	--lock-path=$(BLD_DIR_BIN)/logs/nginx.lock

$(NGINX_CONFIG):
	cd $(NGINX_DIR) && ./configure $(NGINX_CONF_PARAM)

.PHONY: nginx
nginx: $(NGINX_CONFIG)
	@cd $(NGINX_DIR) && make install
	@cd $(BLD_DIR_ENV)/conf; rm `ls | grep -v mime.types`; rm mime.types.default;

.PHONY: clean
clean:
	@echo "--- Cleaning nginx" && echo "running clean"
	@make -C $(NGINX_DIR) clean ||:

