/*
---
description: Any JFrame response that has a root-level child element with the class .partial_refresh will find all elements that have a property defined for data-partial-id that is unique to the response and only update them. If there is a mismatch in the response such that the number of and ids of partials in the previous state do not match the return state, an alert will be shown the user that the entire view will be updated that they can cancel, if they so choose. 
provides: [CCS.JFrame.PartialRefresh]
requires: [/CCS.JFrame, Widgets/ART.Alerts, Table/Table, Widgets/Element.Data]
script: CCS.JFrame.PartialRefresh.js

...
*/
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
(function(){

	var enableLog; //set to true if you want to log messages; left here for convenience.

	CCS.JFrame.addGlobalRenderers({

		/*
			Example w/ partials, container, and lines
			<tbody data-partial-container-id="tbody1">
				<tr data-partial-line-id="tr1">
					<td data-partial-id="id1"></td>
					<td data-partial-id="id2"></td>
				</tr>
			</tbody>

			Example w/ just partials and container
			<div data-partial-container-id="div1">
				<p data-partial-id="p1">foo</p>
				<p data-partial-id="p2">bar</p>
			</div>
		*/

		partialRefresh: function(content){
			var options = content.options;
			//when we load content via ajax, we don't want the response being parsed for partials
			if (options && options.ignorePartialRefresh) return;
			var jState = getJState(this);
			//get the partial containers; containers that have elements in them to be partially refreshed
			var partialContainers = new Element('div').adopt(content.elements).getElements('.partial_refresh');
			var setPrevPath = function(){
				jState.prevPath = options ? options.responsePath : null;
			};
			if (!partialContainers.length) {
				if (enableLog) dbug.log('no partials to refresh, exiting');
				//no partial containers, reset and fall through to other renderers
				setPrevPath();
				jState.partials = null;
				this.enableSpinnerUsage();
				return;
			}
			//get the partials in the containers
			var partials = getPartials(new Element('div').adopt(partialContainers), true);
			//if the options aren't defined or if we didn't auto refresh, reset and
			//return (fall through to other renderers)
			if (!options || !(options.autorefreshed || options.forcePartial)) {
				//...then store the state and render as usual (fall through to other renderers)
				if (enableLog) dbug.log('not auto refreshed (%s), or new path (%s != %s) and not forced (%s), existing partial refresh after setup', !options.autorefreshed, jState.prevPath, options.responsePath, options.forcePartial);
				setPrevPath();
				jState.partials = partials;
				this.disableSpinnerUsage();
				return;
			}

			if (new URI(options.requestPath).toString() != new URI(options.responsePath).toString()) {
				if (enableLog) dbug.warn('detected partial refresh on a possible redirect (the request path (%s) != the response path (%s)), continuing with partial refresh', new URI(options.requestPath).toString(), new URI(options.responsePath).toString());
			}
			setPrevPath();

			//don't show the spinner for partial refreshes
			this.disableSpinnerUsage();

			/*******************************
			FORM HERE ON OUT
			this filter will handle the response; we return true and other renderers are excluded
			UNLESS there is a partial returned that we cannot find the proper place to put it
			(i.e. it has no partial-container).
			*******************************/
			if (enableLog) dbug.log('proceeding with partial refresh');
			//store the path as the current one
			this.currentPath = options.responsePath || this.currentPath;

			//this method destroys a partial given its partial id
			var destroy = function(id){
				//get the element
				var element = jState.partials[id];
				//clean up its behaviors
				this.behavior.cleanup(element);
				//destroy the element
				element.destroy();
				//delete it from the jState
				delete jState.partials[id];
			}.bind(this);

			var checkedPartials = {},
			    update = false,
			    renderedIds = {},
			    renderedPartials = new Elements(),
			    partialClones = {},
			    target = new Element('div');
			//loop through the partials and figure out which ones need updating so that we can 
			//run only those through the filters
			partials.each(function(partial, id) {
				if (enableLog) dbug.log('considering %s for update', id);
				//get the corresponding element in the dom
				var before = jState.partials[id];
				//if there isn't one, or thier raw html don't match, we'll update it, so we must render it
				if (!before || !compare(before, partial)) {
					if (enableLog) dbug.log('preparing %s for update', id);
					//we must preserve the DOM structure to be able to find partial containers and partial lines
					//so clone the partial for rendering
					var clone = partial.clone(true, true);
					target.adopt(clone);
					renderedPartials.push(clone);
					renderedIds[id] = true;
					//store a reference to the clone
					partialClones[id] = clone;
				}
			});
			//render the content
			if (!renderedPartials.length) {
				if (enableLog) dbug.log('no partials for render; exiting quietly');
				//if we aren't updating anything, that's cool, but still call the autorefresh filter
				//to ensure that the frame keeps refreshing
				this.applyFilter('autorefresh', new Element('div'), content);
				//if there is no new content, return true (so no other renderers are called)
				return true;
			}

			//apply all the jframe magic to our filtered content
			if (enableLog) dbug.log('applying filters');
			content.elements = renderedPartials;
			this.applyFilters(target, content);

			//now loop through the partials again and inject them into the DOM structure from the response
			//replacing the original partial with the cloned one
			partials.each(function(partial, id){
				if (enableLog) dbug.log('replacing target with clone');
				var clone = partialClones[id];
				if (clone) {
					//because we're replacing, we need to copy over thier original HTML state for the checksum
					clone.store('partialRefresh:unaltered', partial.retrieve('partialRefresh:unaltered'));
					clone.replaces(partial);
					//and then update the pointer as the clone is now the rendered partial
					partials[id] = clone;
				}
			});

			var prevId;
			if (enableLog) dbug.log('iterating over partials for injection');
			//iterate over all the partials to inject them into the live DOM
			partials.each(function(partial, id){
				if (enableLog) dbug.log('considering %s for injection', id);
				//if it's in a line that's been injected, skip it
				if (!partial.retrieve('partialRefresh:inserted')) {
					//if it was passed through the renderers, it means that it needs an update or insertion
					if (renderedIds[id]) {
						//get the corresponding partial in the DOM
						var before = jState.partials[id];
						//if there's a corresponding partial already in the DOM, replace it
						if (before) {
							if (enableLog) dbug.log('performing update for %s', id);
							partial.replaces(before);
							destroy(id);
						} else {
							//else it's not in the DOM
							//look to see if this partial is in a line item (for example, the tr for a td that is a partial)
							var line = getPartialLine(partial);
							//if there is no line, inject it into the DOM in the container
							if (!line) {
								if (prevId) {
									if (enableLog) dbug.log('injecting line for %s after previous item (%s)', id, prevId);
									//if this isn't the first one, inject it after the previous id
									partial.inject(jState.partials[prevId], 'after');
								} else {
									//find the container and inject it as the first item there
									var containers = getPartialContainers(partial, this);
									if (containers.DOMcontainer) {
										if (enableLog) dbug.log('injecting %s into top of container (%o)', id, containers.DOMcontainer);
										partial.inject(containers.DOMcontainer, 'top');
									} else {
										//else, we don't know where to inject it
										dbug.warn('Could not inject partial (%o); no container or previous item found.', partial);
										//fall through to other renderers (i.e. refresh the whole view)
										return;
									}
								}
							} else {
								if (enableLog) dbug.log('preparing line for injection');
								//there is a line, so we inject it instead of the partial

								//get the previous line (from the response)
								var prevLine = line.getPrevious('[data-partial-line-id]'),
								    prevLineInDOM;
								//now find it's counterpart in the live DOM
								if (prevLine) prevLineInDOM = $(this).getElement('[data-partial-line-id=' + prevLine.get('data', 'partial-line-id') + ']');
								//if it's there, inject this line after it
								if (prevLineInDOM) {
									if (enableLog) dbug.log('injecting line (%o) after previous line (%o)', line, prevLine);
									line.inject(prevLineInDOM, 'after');
								} else {
									//else this is the first line, so inject it at the top of the container
									var lineContainers = getPartialContainers(partial, this);
									if (lineContainers.DOMcontainer) {
										if (enableLog) dbug.log('injecting line (%o) into top of container (%o)', line, lineContainers.DOMcontainer);
										line.inject(lineContainers.DOMcontainer, 'top');
									} else {
										//else, we don't know where to inject it
										dbug.warn('Could not inject partial (%o) in line (%o); no container or previous item found.', partial, line);
										//fall through to other renderers (i.e. refresh the whole view)
										return;
									}
								}
								//store the fact that we just injected all the partials in this line
								line.getElements('[data-partial-id]').store('partialRefresh:inserted', true);
							}
						}
					}
				}
				if (renderedIds[id]) jState.partials[id] = partial;
				prevId = id;
			}, this);
			
			//given a line, destroy it
			var destroyLine = function(line){
				if (enableLog) dbug.log('destroying line:', line);
				this.behavior.cleanup(line);
				line.destroy();
			}.bind(this);

			var prevLine;
			//for any partials that were in the DOM but not in the response, remove them
			jState.partials.each(function(partial, id){
				//if the partial is in the DOM but not the response
				if (!partials[id]) {
					//get its line; assume that we have to remove that, too
					var line = getPartialLine(partial);
					if (enableLog) dbug.log('destroying %s', id, line);
					//destroy the partial
					destroy(id);
					//if we've reached a new line, destroy the old one
					if (prevLine && line != prevLine) destroyLine(prevLine);
					prevLine = line;
				}
			});
			//if we ended with a previous line defined, destroy it.
			if (prevLine) destroyLine(prevLine);

			//we've updated the display, so tell filters that are waiting that they may need to update their display, too
			this.behavior.fireEvent('show');
			//prevent other renderers from handling the response
			return true;
		}

	});

	var jframeStates = new Table();

	//gets the state for the given jframe
	var getJState = function(jframe) {
		var jState = jframeStates.get(jframe);
		if (!jState) {
			jState = {};
			jframeStates.set(jframe, jState);
		}
		return jState;
	};

	//gets all the partial elements to refresh from the specified container
	//if *store* == true, then store this state on each element as the original,
	//unaltered response
	var getPartials = function(container, store) {
		if (!container.innerHTML.contains('data-partial-id')) return {};
		var partials = {};
		//get all the elements with a partial id
		container.getElements('[data-partial-id]').each(function(partial){
			//store a pointer to that element to return it
			partials[partial.get('data', 'partial-id')] = partial;
			//if instructed to, store the original state of the response before it was altered by any filter
			if (store) partial.store('partialRefresh:unaltered', partial.innerHTML);
		});
		return $H(partials);
	};

	//given a partial, attempts to find the line it is in
	//example: for a td that is a partial, it may have the tr as its line
	var getPartialLine = function(partial){
		return partial.getParent('[data-partial-line-id]');
	};
	//given a partial, attempts to find the container it is in
	//for example, for a td that is a partial, it may have the tr as its line and the table as its container
	var getPartialContainers = function(partial, jframe){
		var containers = {
			container: partial.getParent('[data-partial-container-id]')
		};
		if (containers.container) {
			containers.DOMcontainer = $(jframe).getElement('[data-partial-container-id=' + 
			  containers.container.get('data', 'partial-container-id') + ']');
		}
		return containers;
	};

	//given two partials, compares their raw HTML before they were parsed by filters
	var compare = function(before, after){
		return before.retrieve('partialRefresh:unaltered') == after.retrieve('partialRefresh:unaltered');
	};

})();