/*// Licensed to Cloudera, Inc. under one
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
// limitations under the License.*/
/*
---

script: Shell.js

description: Defines Shell; a Hue application that extends CCS.JBrowser.

authors:
- Hue

requires: [ccs-shared/CCS.JBrowser, ccs-shared/CCS.Request, Core/Element, Core/Native]
provides: [Shell]

...
*/
ART.Sheet.define('window.art.browser.shell', {
  'min-width': 620
});

(function(){
  var expressions = [
    {
      expr: /&/gm,
      replacement: '&amp;'
    },
    {
      expr: /</gm,
      replacement: '&lt;'
    },
    {
      expr: />/gm,
      replacement: '&gt;'
    },
    {
      expr: /"/gm,
      replacement: '&quot;'
    },
    {
      expr: /\n/g,
      replacement: "<br>"
    }
  ];
  
  String.implement({
    escapeHTML: function(){
      var cleaned = this;
      expressions.each(function(expression) {
        cleaned = cleaned.replace(expression.expr, expression.replacement);
      });
      return cleaned;
    }
  });
})();

var Shell = new Class({
  Extends: CCS.JBrowser,
  options: {
    displayHistory: false,
    className: 'art browser logo_header shell'
  },
  
  initialize: function(path, options){
    this.parent(path || '/shell/', options);
    if(options && options.shellId){
      this.shellId = options.shellId;
      var loadEvent = this.startRestore.bind(this);
    }else{
      var loadEvent = this.setup.bind(this);
    }
    this.addEvents({
      load: loadEvent
    });
  },
  
  startRestore: function(view){
    this.view = view;
    this.restoreReq = new Request.JSON({
      method: 'post',
      url: '/shell/restore_shell',
      onSuccess: this.restoreCompleted.bind(this),
      onFailure: this.restoreFailed.bind(this)
    });
    var shellId = this.shellId;
    this.restoreReq.send({
      data: 'shellId='+shellId
    });
  },
  
  restoreCompleted: function(json, text){
    this.restoreReq = null;
    if(json.success){
      this.view = null;
      this.nextChunkId = json.nextChunkId;
      this.setupTerminalFromPreviousOutput(json.output);
    }else{
      this.restoreFailed();
    }
  },
  
  restoreFailed: function(){
    this.restoreReq = null;
    var view = this.view;
    this.view = null;
    this.setup(view);
  },
  
  setup: function(view) {
    this.shellCreated = false;
    this.shellKilled = false;
    this.jframe.markForCleanup(this.cleanUp.bind(this));

    this.shellTypesReq = new Request.JSON({
      method: 'get',
      url: '/shell/get_shell_types',
      onSuccess: this.shellTypesReqCompleted.bind(this),
      onFailure: this.shellTypesReqFailed.bind(this)
    });

    this.shellTypesReq.send();
  },
  
  shellTypesReqCompleted: function(json, text){
    this.shellTypesReq = null;
    if(json.success){
      this.setupTerminalForSelection(json.shellTypes);
    }else if(json.notLoggedIn){
      this.alert('Error', 'You are not logged in. Please reload your browser window and log in.');
    }else if(json.shellLimitReached){
      this.alert('Error', 'You already have the maximum number of shells open. Please close one to open a new shell.');
    }
  },
  
  shellTypesReqFailed: function(){
    this.shellTypesReq = null;
    this.background = $(this).getElement('.jframe_contents');
    this.background.setStyle("background-color", "#cccccc");
    this.alert('Error',"Could not retrieve available shell types. Is the Tornado server running?");
  },
  
  setupTerminalFromPreviousOutput: function(initVal){
    this.background = $(this).getElement('.jframe_contents');
    this.container = $(this).getElement('.jframe_padded');
    this.output = new Element('span');
    this.input = new Element('textarea', {
      events: {
        keypress: this.handleKeyPress.bind(this)
      }
    });

    this.button = new Element('input', {
      type:'button',
      value:'Send command',
      'class':'ccs-hidden',
      events: {
        click:this.sendCommand.bind(this)
      }
    });

    this.container.adopt([this.output, this.input, this.button]);
    this.output.set("html", initVal.escapeHTML());

    this.jframe.scroller.setOptions({
      duration: 200
    });
    this.jframe.scroller.toBottom();
    this.input.focus();

    //If the user clicks anywhere in the jframe, focus the textarea.
    this.background.addEvent("click", this.focusInput.bind(this));

    //The perpetually open output request. We always keep this request
    //open so the server has a way of pushing data to the client whenever
    //data is received.
    this.outputReq = new Request.JSON({
      method: 'post',
      url: '/shell/retrieve_output',
      onSuccess: this.outputReceived.bind(this),
      onFailure: this.openOutputChannel.bind(this)
    });

    //The command-sending request.  We don't need this to be perpetually open,
    //but rather to be something that we can reuse repeatedly to send commands
    //to the subprocess running on the server.
    this.commandReq = new Request.JSON({
      method: 'post',
      url: '/shell/process_command',
      onSuccess: this.commandProcessed.bind(this)
    });

    //The timeout is to avoid the "loading" icon of the browser spinning forever since this request
    //will always be kept open.
    this.openOutputChannel.delay(0, this);
  },
  
  setupTerminalForSelection: function(shellTypes){
    this.background = $(this).getElement('.jframe_contents');
    this.container = $(this).getElement('.jframe_padded');
    
    this.output = new Element('span');
    this.input = new Element('textarea', {
      events: {
        keypress: this.handleKeyPressForSelection.bind(this)
      }
    });
    this.button = new Element('input', {
      type:'button',
      value:'Send command',
      'class':'ccs-hidden',
      events: {
        click:this.handleShellSelection.bind(this)
      }
    });
    
    this.container.adopt([this.output, this.input, this.button]);
    this.processShellTypes(shellTypes);
    
    this.jframe.scroller.setOptions({
      duration: 200
    });
    this.jframe.scroller.toBottom();
    this.input.focus();
    
    //If the user clicks anywhere in the jframe, focus the textarea.
    this.background.addEvent("click", this.focusInput.bind(this));
  },
  
  processShellTypes: function(shellTypes){
    this.choices = new Array();
    this.choicesHTML = "Please select the shell to start. Your choices are:\n".escapeHTML();
    for(var i = 0 ; i<shellTypes.length; i++){
      var choiceLine = (i+1).toString()+". "+shellTypes[i].niceName+"\n";
      this.choicesHTML += choiceLine.escapeHTML();
      this.choices.push(shellTypes[i].keyName);
    }
    this.choicesHTML += ">".escapeHTML();
    this.output.set('html', this.choicesHTML);
  },
  
  focusInput: function(){
    if(!this.input.get("disabled")){
      this.input.focus();
    }
  },

  handleKeyPressForSelection: function(event){
    if(event.key=="enter"){
      this.handleShellSelection();
      event.stop();
    }
    //If we need to have the textarea grow, we can only do that after the
    //contents of the textarea have been updated. So let's set a timeout
    //that gets called as soon as the stack of this event handler
    //returns.
    this.resizeInput.delay(0, this);
  },

  resizeInput: function(){
    //In Firefox, we can't resize the textarea unless we first clear its
    //height style property.
    if(Browser.Engine.gecko){
      this.input.setStyle("height","");
    }
    this.input.setStyle("height", this.input.get("scrollHeight"));
  },

  handleShellSelection: function(){
    var selection = parseInt(this.input.get("value"));
    if(!selection || selection<=0 || selection > this.choices.length){
      this.output.set('html', this.output.get('html')+this.input.get('value').escapeHTML());
      var response = '\nInvalid choice: "'+this.input.get("value")+'"\n\n';
      response = response.escapeHTML();
      response += this.choicesHTML;
      this.output.set("html", this.output.get("html")+response);
      this.input.set("value", "");
      this.input.focus();
      return;
    }
    this.output.set('html', this.output.get('html')+(this.input.get('value')+"\n").escapeHTML());
    this.input.set("value", "");
    var keyName = this.choices[selection-1];
    this.registerReq = new Request.JSON({
      method: 'post',
      url: '/shell/create',
      onSuccess: this.registerCompleted.bind(this),
      onFailure: this.registerFailed.bind(this)
    });
    this.registerReq.send({ data: "keyName="+keyName })
  },
  
  registerFailed: function(){
    this.registerReq = null;
    this.background = $(this).getElement('.jframe_contents');
    this.background.setStyle("background-color", "#cccccc");
    this.alert('Error',"Error creating shell. Is the shell server running?");
  },

  registerCompleted: function(json, text){
    this.registerReq = null;
    if(!json.success){
      this.background.setStyle("background-color", "#cccccc");
      if(json.shellLimitReached){
        this.alert('Error', "You already have the maximum number of shells open. Please close one to open a new shell.");
      }else if(json.notLoggedIn){
        this.alert('Error', 'You are not logged in. Please reload your browser window and log in.');
      }else if(json.shellCreateFailed){
        this.alert('Error', 'Could not create any more shells. Please try again soon.');
      }
    }else{
      this.shellCreated = true;
      this.shellId = json.shellId;
      this.options.shellId = json.shellId;
      this.nextChunkId = 0;
      this.setupTerminalForShellUsage();
    }
  },
  
  setupTerminalForShellUsage: function(){
    this.input.removeEvents('keypress');
    this.button.removeEvents('click');
    
    //The perpetually open output request. We always keep this request
    //open so the server has a way of pushing data to the client whenever
    //data is received.
    this.outputReq = new Request.JSON({
      method: 'post',
      url: '/shell/retrieve_output',
      onSuccess: this.outputReceived.bind(this),
      onFailure: this.openOutputChannel.bind(this)
    });
    
    //The command-sending request.  We don't need this to be perpetually open,
    //but rather to be something that we can reuse repeatedly to send commands
    //to the subprocess running on the server.
    this.commandReq = new Request.JSON({
      method: 'post',
      url: '/shell/process_command',
      onSuccess: this.commandProcessed.bind(this)
    });
    
    this.input.addEvent('keypress', this.handleKeyPress.bind(this));
    this.button.addEvent('click', this.sendCommand.bind(this));
    
    this.jframe.scroller.toBottom();
    this.input.focus();
    
    //The timeout is to avoid the "loading" icon of the browser spinning forever since this request
    //will always be kept open.
    this.openOutputChannel.delay(0, this);
  },
  
  handleKeyPress: function(event){
    if(event.key=="enter"){
      this.sendCommand();
    }
    //If we need to have the textarea grow, we can only do that after the
    //contents of the textarea have been updated. So let's set a timeout
    //that gets called as soon as the stack of this event handler
    //returns.
    this.resizeInput.delay(0, this);
  },
  
  sendCommand: function(){
    var lineToSend = this.input.get("value");
    var shellId = this.shellId;
    this.disableInput();
    this.commandReq.send({
      data: 'lineToSend='+lineToSend+'&shellId='+shellId
    });
  },
  
  commandProcessed: function(json, text){
    if(json.success){
      this.enableInput();
      this.input.setStyle("height","auto");
      this.input.set("value", "");
    }else{ 
      this.background.setStyle("background-color", "#cccccc");
      if(json.noShellExists){
        this.alert("Error", "This shell does not exist any more. Please restart this app.");
      }else if(json.notLoggedIn){
        this.alert("Error", "You are not logged in. Please log in to use this app.");
      }else if(json.shellKilled){
        this.alert("Error", "This shell has been killed. Please restart this app.");
      }else if(json.bufferExceeded){
        this.alert("Error", "You have entered too many commands. Please try again. If this problem persists, please restart this app.");
      }
    }
  },
  
  openOutputChannel:function(){
    var params = [ [ "shellId", this.shellId ], [ "nextChunkId", this.nextChunkId] ];
    var serializedParams = [];
    params.each(function(pair){
      serializedParams.push(pair.join("="));
    });
    var serializedData = serializedParams.join("&");
    this.outputReq.send({
      data: serializedData
    });
  },
  
  outputReceived:function(json, text){
    if(json.alive || json.exited){
      var escapedText = json.output.escapeHTML();
      this.output.set("html",this.output.get('html')+escapedText);
      this.jframe.scroller.toBottom();
      this.nextChunkId = json.nextChunkId;
      if(json.alive || json.moreOutputAvailable){
        //We have to use a timeout because re-firing the request in the onSuccess handler of
        //the previous use of the request object causes buggy behavior.
        //Using .delay(0, this) also causes the same behavior.
        setTimeout(this.openOutputChannel.bind(this), 0);
      }
      if(json.exited){
        this.disableInput();
        this.input.setStyle("display", "none");
        this.shellKilled = true;
      }
    }else if(json.periodicResponse){
      //We have to use a timeout because re-firing the request in the onSuccess handler of
      //the previous use of the request object causes buggy behavior.
      //Using .delay(0, this) also causes the same behavior.
      setTimeout(this.openOutputChannel.bind(this), 0);
    }else{
      this.background.setStyle("background-color", "#cccccc");
      if(json.noShellExists){
        this.alert("Error", "The shell no longer exists. Please restart this app.");
      }else if(json.notLoggedIn){
        this.alert("Error", "You are not logged in. Please log in to use this app.");
      }else if(json.shellKilled){
        this.alert("Error", "This shell has been killed. Please restart this app.");
      }
    }
  },
  
  enableInput:function(){
    this.button.set('disabled', false);
    this.input.set({
      disabled: false,
      styles: {
        cursor: 'text'
      }
    }).focus();
  },
  
  disableInput:function(){
    this.button.set('disabled', true);
    this.input.set({
      disabled: true,
      styles: {
        cursor: 'default'
      }
    }).blur();
  },
  
  cleanUp:function(){
    //These might not exist any more if they completed already.
    if(this.shellTypesReq){
      this.shellTypesReq.cancel();
    }
    if(this.registerReq){
      this.registerReq.cancel();
    }
    if(this.restoreReq){
      this.restoreReq.cancel();
    }

    //These requests might not exist if we haven't got around to sending them yet.
    if(this.outputReq){
      this.outputReq.cancel();
    }
    if(this.commandReq){
      this.commandReq.cancel();
    }

    if(this.shellCreated && !this.shellKilled){
      //A one-time request to tell the server to kill the subprocess if it's still alive.
      var shellId = this.shellId;
      var req = new Request.JSON({
        method: 'post',
        url: '/shell/kill_shell'
      });
      req.send({
        data: 'shellId='+shellId
      });
    }
  }
});
