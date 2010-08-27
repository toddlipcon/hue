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
    $(this).getElement('.plus_button').addEvent("click", function(){ 
      CCS.Dock.launchApp( { preventDefault: function(){}}, document.getElementById("ccs-shell-menu"), true);
    });
    
    // Set up some state shared between "fresh" and "restored" shells.
    this.previousCommands = new Array();
    this.currentCommandIndex = -1;
    
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
    this.input.addEvent("keydown", this.handleKeyDown.bind(this));
    this.button.addEvent("click", this.sendCommand.bind(this)); //TODO: Pull into declaration
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
      this.previousCommands = json.commands;
      this.currentCommandIndex = this.previousCommands.length - 1;
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

  setupTerminalForShellUsage: function(){
    // Set up the DOM
    this.container.adopt([this.output, this.input, this.button]);
    
    // If the user clicks anywhere in the jframe, focus the textarea.
    this.background.addEvent("click", this.focusInput.bind(this));

    this.shellCreated = true;
    
    this.focusInput();

    // Register the shell we have with CCS.Desktop so we can be included in its output channel.
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
      this.processShellTypes(json.shellTypes);
    }else if(json.notLoggedIn){
      this.errorMessage('Error', 'You are not logged in. Please reload your browser window and log in.');
    }
  },

  shellTypesReqFailed: function(){
    this.shellTypesReq = null;
    this.errorMessage('Error',"Could not retrieve available shell types. Is the Tornado server running?");
  },

  processShellTypes: function(shellTypes){
    this.background.setStyle("background-color","#aaaaaa");
    var table = new Element("table");
    this.container.grab(table);
    for(var i = 0 ; i<shellTypes.length; i++){
      var tr = new Element("tr", {
        'class':'fakelink'
      });
      var left = new Element("td", {
        'class':'left'
      }); 
      var div = new Element("div");
      left.grab(div);
      var middle = new Element("td", {
        html:shellTypes[i].niceName.escapeHTML(),
        'class':'middle'
      });
      var right = new Element("td", {
        'class':'right'
      });
      div = new Element ("div");
      right.grab(div);
      tr.adopt([left, middle, right]);
      table.grab(tr);
      tr.addEvent('click', this.handleShellSelection.bind(this, [shellTypes[i].keyName]));
    }
  },

  handleShellSelection: function(keyName){
    this.registerReq = new Request.JSON({
      method: 'post',
      url: '/shell/create',
      onSuccess: this.registerCompleted.bind(this),
      onFailure: this.registerFailed.bind(this)
    });
    this.registerReq.send({ data: "keyName="+keyName });
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

  registerFailed: function(){
    this.registerReq = null;
    this.choices = null;
    this.choicesText = null;
    this.errorMessage('Error',"Error creating shell. Is the shell server running?");
  },

  registerCompleted: function(json, text){
    this.registerReq = null;
    if(!json.success){
      if(json.notLoggedIn){
        this.errorMessage('Error', 'You are not logged in. Please reload your browser window and log in.');
      }else if(json.shellCreateFailed){
        this.errorMessage('Error', 'Could not create any more shells. Please try again soon.');
      }
    }else{
      this.background.setStyle("background-color","#ffffff");
      this.shellCreated = true;
      this.shellId = json.shellId;
      this.options.shellId = json.shellId;
      this.nextChunkId = 0;
      this.jframe.collectElement(this.container);
      this.container.empty();
      this.setupTerminalForShellUsage();
    }
  },
  
  showPreviousCommand: function(){
    if(this.currentCommandIndex < 0 || this.currentCommandIndex >= this.previousCommands.length){
      this.currentCommandIndex = this.previousCommands.length-1;
    }
    var oldCommand = this.previousCommands[this.currentCommandIndex];
    if(oldCommand){
      this.input.set('value', oldCommand);
      this.currentCommandIndex--;
      this.focusInput();
    }
  },
  
  showNextCommand: function(){
    if(this.currentCommandIndex < 0 || this.currentCommandIndex >= this.previousCommands.length){
      this.currentCommandIndex = this.previousCommands.length?0:-1;
    }
    var oldCommand = this.previousCommands[this.currentCommandIndex];
    if(oldCommand){
      this.input.set('value', oldCommand);
      this.currentCommandIndex++;
      this.focusInput();
    }
  },
  
  handleUpKey: function(){
    var tempInputValue = this.tempInputValue;
    this.tempInputValue = null;
    if(tempInputValue === this.input.get("value")){
      this.showPreviousCommand();
    }
  },
  
  handleDownKey: function(){
    var tempInputValue = this.tempInputValue;
    this.tempInputValue = null;
    if(tempInputValue === this.input.get("value")){
      this.showNextCommand();
    }
  },

  handleKeyDown: function(event){
    if(event.key=="enter"){
      this.recordCommand();
      this.sendCommand();
    }else if(event.key=="up"){
      this.tempInputValue = this.input.get("value");
      // The delay is to deal with a problem differentiating "&" and "up" in Firefox.
      this.handleUpKey.delay(5, this);
    }else if(event.key=="down"){
      this.tempInputValue = this.input.get("value");
      // The delay is to deal with a problem differentiating "(" (left paren) and "down" in Firefox.
      this.handleDownKey.delay(5, this);
    }else if(event.key=="tab"){
      event.stop();
    }
    //If we need to have the textarea grow, we can only do that after the
    //contents of the textarea have been updated. So let's set a timeout
    //that gets called as soon as the stack of this event handler
    //returns.
    this.resizeInput.delay(0, this);
  },
  
  recordCommand: function(){
    var enteredCommand = this.input.get("value");
    if(enteredCommand){
      this.previousCommands.push(enteredCommand);
      this.currentCommandIndex = this.previousCommands.length - 1;
    }
  },

  sendCommand: function(){
    var enteredCommand = this.input.get("value");
    var lineToSend = encodeURIComponent(enteredCommand);
    dbug.log(lineToSend);
    var shellId = this.shellId;
    this.disableInput();
    dbug.log(lineToSend);
    dbug.log(escape(" "));
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
        this.shellExited();
      }
    }else{
      if(json.noShellExists){
        this.shellExited();
      }else if(json.notLoggedIn){
        this.errorMessage("Error", "You are not logged in. Please log in to use this app.");
      }else if(json.shellKilled){
        this.shellExited();
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

  errorStatus:function(){
    this.disableInput();
    this.background.setStyle("background-color", "#cccccc");
  },
  
  errorMessage:function(title, message){
    this.errorStatus();
    this.alert(title, message);
  },
  
  shellExited:function(){
    this.errorStatus();
    this.appendToOutput("\n[Process completed]");
    this.shellKilled = true;
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
    
    //Clear out this.options.shellId and this.shellId, but save the value in a local variable
    //for the purposes of this function.
    this.options.shellId = null;
    var shellId = this.shellId;
    this.shellId = null;
    
    //Tell CCS.Desktop to stop listening for shellId. Important to do this before
    //sending the kill shell request because then the resulting output doesn't cause
    //a non-existent callback to be called.
    if(shellId){
      CCS.Desktop.stopShellListener(shellId);
      if(this.shellCreated && !this.shellKilled){
        //A one-time request to tell the server to kill the subprocess if it's still alive.
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
