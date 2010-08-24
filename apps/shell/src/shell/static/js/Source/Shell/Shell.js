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
    }
    this.addEvent("load", this.startShell.bind(this));
  },

  startShell: function(view){
    // Set up some state shared between "fresh" and "restored" shells.

    this.jframe.markForCleanup(this.cleanUp.bind(this));
    this.shellKilled = false;

    this.background = $(this).getElement('.jframe_contents');
    this.background.setStyle("background-color", "#ffffff");
    this.container = $(this).getElement('.jframe_padded');
    this.output = new Element('span', {
      'class':'fixed_width_font'
    });
    this.input = new Element('textarea', {
      'class':'fixed_width_font'
    });
    this.button = new Element('input', {
      type:'button',
      value:'Send command',
      'class':'ccs-hidden'
    });
    this.jframe.scroller.setOptions({
      duration: 200
    });

    // The command-sending request.  We don't need this to be perpetually open,
    // but rather to be something that we can reuse repeatedly to send commands
    // to the subprocess running on the server.
    this.commandReq = new Request.JSON({
      method: 'post',
      url: '/shell/process_command',
      onSuccess: this.commandProcessed.bind(this)
    });

    // Now let's kick off the appropriate thing, either a new shell or a restore.
    if(this.shellId){
      this.startRestore(view);
    }else{
      this.setup(view);
    }
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
    this.shellId = null;
    var view = this.view;
    this.view = null;
    this.setup(view);
  },

  setupTerminalFromPreviousOutput: function(initVal){
    // Wire up the appropriate handlers
    this.input.addEvent("keypress", this.handleKeyPress.bind(this));
    this.button.addEvent("click", this.sendCommand.bind(this));

    // Set up the DOM
    this.container.adopt([this.output, this.input, this.button]);
    this.appendToOutput(initVal);

    // Scroll the jframe and focus the input
    this.jframe.scroller.toBottom();
    this.input.focus();

    // If the user clicks anywhere in the jframe, focus the textarea.
    this.background.addEvent("click", this.focusInput.bind(this));

    // To mimic creation, let's set this.shellCreated to true.
    this.shellCreated = true;

    // Register the shell we have with CCS.Desktop, so we can be included in the output channel it has.
    CCS.Desktop.listenForShell(this.shellId, this.nextChunkId, this.outputReceived.bind(this));
  },

  focusInput: function(){
    if(!this.input.get("disabled")){
      this.input.focus();
    }
  },

  setup: function(view) {
    this.shellCreated = false;
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
      this.errorMessage('Error', 'You are not logged in. Please reload your browser window and log in.');
    }
  },

  shellTypesReqFailed: function(){
    this.shellTypesReq = null;
    this.errorMessage('Error',"Could not retrieve available shell types. Is the Tornado server running?");
  },

  setupTerminalForSelection: function(shellTypes){
    // Wire up the appropriate events
    this.input.addEvent("keypress", this.handleKeyPressForSelection.bind(this));
    this.button.addEvent("click", this.handleShellSelection.bind(this));

    // Set up the DOM
    this.container.adopt([this.output, this.input, this.button]);
    this.processShellTypes(shellTypes);

    //Scroll to the bottom of the jframe and focus the input.
    this.jframe.scroller.toBottom();
    this.input.focus();

    //If the user clicks anywhere in the jframe, focus the textarea.
    this.background.addEvent("click", this.focusInput.bind(this));
  },

  processShellTypes: function(shellTypes){
    this.choices = new Array();
    this.choicesText = "Please select the shell to start. Your choices are:\n";
    for(var i = 0 ; i<shellTypes.length; i++){
      var choiceLine = (i+1).toString()+". "+shellTypes[i].niceName+"\n";
      this.choicesText += choiceLine;
      this.choices.push(shellTypes[i].keyName);
    }
    this.choicesText += ">";
    this.appendToOutput(this.choicesText);
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

  appendToOutput:function(text){
    this.output.set('html', this.output.get('html')+text.escapeHTML());
  },

  handleShellSelection: function(){
    var enteredText = this.input.get("value");
    this.appendToOutput(enteredText+"\n");
    this.input.set("value", "");

    var selection = parseInt(enteredText);
    if(!selection || selection<=0 || selection > this.choices.length){
      var response = 'Invalid choice: "'+enteredText+'"\n\n'+this.choicesText;
      this.appendToOutput(response);
      this.input.focus();
      return;
    }

    var keyName = this.choices[selection-1];
    this.registerReq = new Request.JSON({
      method: 'post',
      url: '/shell/create',
      onSuccess: this.registerCompleted.bind(this),
      onFailure: this.registerFailed.bind(this)
    });
    this.disableInput();
    this.registerReq.send({ data: "keyName="+keyName })
  },

  setupTerminalForShellUsage: function(){
    // Remove previous events
    this.input.removeEvents('keypress');
    this.button.removeEvents('click');

    // Now wire up the appropriate ones
    this.input.addEvent('keypress', this.handleKeyPress.bind(this));
    this.button.addEvent('click', this.sendCommand.bind(this));

    // Now scroll to the bottom of the jframe and focus the input.
    this.jframe.scroller.toBottom();
    this.input.focus();

    // Register the shell we have with CCS.Desktop so we can be included in its output channel.
    CCS.Desktop.listenForShell(this.shellId, this.nextChunkId, this.outputReceived.bind(this));
  },

  registerFailed: function(){
    this.registerReq = null;
    this.choices = null;
    this.choicesText = null;
    this.errorMessage('Error',"Error creating shell. Is the shell server running?");
  },

  registerCompleted: function(json, text){
    this.registerReq = null;
    this.choices = null;
    this.choicesText = null;
    if(!json.success){
      if(json.notLoggedIn){
        this.errorMessage('Error', 'You are not logged in. Please reload your browser window and log in.');
      }else if(json.shellCreateFailed){
        this.errorMessage('Error', 'Could not create any more shells. Please try again soon.');
      }
    }else{
      this.shellCreated = true;
      this.shellId = json.shellId;
      this.options.shellId = json.shellId;
      this.nextChunkId = 0;
      this.output.set("html", "");
      this.enableInput();
      this.setupTerminalForShellUsage();
    }
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
      if(json.noShellExists){
        this.errorMessage("Error", "This shell does not exist any more. Please restart this app.");
      }else if(json.notLoggedIn){
        this.errorMessage("Error", "You are not logged in. Please log in to use this app.");
      }else if(json.shellKilled){
        this.errorMessage("Error", "This shell has been killed. Please restart this app.");
      }else if(json.bufferExceeded){
        this.errorMessage("Error", "You have entered too many commands. Please try again. If this problem persists, please restart this app.");
      }
    }
  },

  outputReceived: function(json){
    if(json.alive || json.exited){
      this.appendToOutput(json.output);
      this.jframe.scroller.toBottom();
      if(json.exited){
        this.disableInput();
        this.input.setStyle("display", "none");
        this.shellKilled = true;
      }
    }else{
      if(json.noShellExists){
        this.errorMessage("Error", "The shell no longer exists. Please restart this app.");
      }else if(json.notLoggedIn){
        this.errorMessage("Error", "You are not logged in. Please log in to use this app.");
      }else if(json.shellKilled){
        this.errorMessage("Error", "This shell has been killed. Please restart this app.");
      }
    }
  },

  enableInput:function(){
    this.button.set('disabled', false);
    this.input.set({
      disabled: false,
      styles: {
        cursor: 'text',
        display: ''
      }
    }).focus();
  },

  disableInput:function(){
    this.button.set('disabled', true);
    this.input.set({
      disabled: true,
      styles: {
        cursor: 'default',
        display: 'none'
      }
    }).blur();
  },

  errorMessage:function(title, message){
    this.disableInput();
    this.background.setStyle("background-color", "#cccccc");
    this.alert(title, message);
  },

  cleanUp:function(){
    //These might not exist any more if they completed already or we quit before they were created.
    if(this.shellTypesReq){
      this.shellTypesReq.cancel();
    }
    if(this.registerReq){
      this.registerReq.cancel();
    }
    if(this.restoreReq){
      this.restoreReq.cancel();
    }
    if(this.commandReq){
      this.commandReq.cancel();
    }

    //Tell CCS.Desktop to stop listening for this shellId. Important to do this before
    //sending the kill shell request because then the resulting output doesn't cause
    //a non-existent callback to be called.
    if(this.shellId){
      CCS.Desktop.stopShellListener(this.shellId);
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
  }
});
