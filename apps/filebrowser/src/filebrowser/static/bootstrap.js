// Licensed to Cloudera, Inc. under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  Cloudera, Inc. licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
CCS.Desktop.register({
	FileBrowser: {
		name: 'File Browser',
		css: '/filebrowser/static/css/fb.css',
		require: ['filebrowser/CCS.FileBrowser'],
		launch: function(path, options){
			return new CCS.FileBrowser(path || 'filebrowser/view/?default_to_home=1', options);
		},
		menu: {
			id: 'ccs-filebrowser-menu',
			img: {
				src: '/filebrowser/static/art/icon.png'
			}
		},
		help: '/help/filebrowser/'
	},
	FileViewer: {
		name: 'File Viewer',
		css: '/filebrowser/static/css/fb.css',
		launch: function(path, options){
			return new CCS.FileViewer(path, options);
		},
		require: ['CCS.FileViewer'],
		help: '/help/filebrowser/'
		
	},
	FileEditor: {
		name: 'File Editor',
		css: '/filebrowser/static/css/fb.css',
		launch: function(path, options){
			return new CCS.FileEditor(path, options);
		},
		require: ['CCS.FileEditor'],
		help: '/help/filebrowser/'
	}
});
