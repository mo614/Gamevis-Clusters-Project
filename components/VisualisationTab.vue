<template>
	<div class="row app-row__main">
		<div class="col-xs-4 main-panel__sidebar">
			<form class="form-horizontal">
				<div class="form-group">
					<label class="col-sm-4">Title</label>
					<div class="col-sm-8">
						<input type="text" class="form-control" v-model="title">
					</div>
				</div>

				<div class="form-group">
					<label class="col-sm-4">Game/Level</label>
					<div class="col-sm-8">
						<gv-game-level-select class="col-sm-8" :selected.sync="gameLevel"></gv-game-level-select>
					</div>
				</div>

				<div class="form-group">
					<label class="col-sm-12">Sessions</label>

					<div class="col-sm-12">
						<gv-session-select :selected.sync="sessions" :game-level="gameLevel" :events.sync="allEvents"></gv-session-select>
					</div>
				</div>

				<label>Events</label>
				<gv-event-list :all="allEvents" :selected.sync="events" :sessions="sessions" :scene="scene"></gv-event-list>
                
                <div class="form-group">
                    <label class="col-sm-4" id="clustersLabel" style=>Clusters</label>
                    
                    <table>
                        <tbody id="clusterColorTable" style="display:none">
                            <tr>
                                <td>Cluster</td>
                                <td>Colour</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

				<div class="form-group-flex" id="visualiseButtonDiv">
					<button type="submit" class="btn btn-primary btn-lg btn-block" @click.prevent="visualise" :disabled="!readyToVisualise">
						<span class="glyphicon glyphicon-eye-open"></span>
						Visualise
					</button>

					<button type="button" class="btn btn-default btn-lg" @click="save">
						<span class="glyphicon glyphicon-floppy-save"></span>
					</button>
                    
                    
				</div>
			</form>
		</div>

		<div class="col-xs-8">
			<gv-timeline v-ref:timeline :items="timeline.items" :groups="timeline.groups"></gv-timeline>
			<gv-webgl-renderer v-ref:renderer :scene.sync="scene" :camera.sync="camera"></gv-webgl-renderer>
            <gv-gauge v-ref:gauge id="gaugeDiv" style="position:absolute; display:none;"></gv-gauge>
		</div>
	</div>
</template>

<script type="text/babel">
	/**
	 * Component for rendering continuous (connected line) visualisations.
	 * @module components/VisualisationTab
	 *
	 * @listens render
	 * @listens postrender
	 *
	 * @param {string} title - Two way. Tab title
	 */

	/**
	 * Per-frame event for updating internal state before render.
	 *
	 * @event updateFrame
	 * @global
	 * @type {object}
	 * @property {OverviewData} overviewData - Overview data for this level
	 */

	/**
	 *
	 * @event visualise
	 * @global
	 * @type {object}
	 * @property {OverviewData} overviewData - Overview data for this level
	 */

	/**
	 * @typedef {object} OverviewData
	 * @global
	 * @property {number} pos_x - World-space X position of the top-left corner of the overview
	 * @property {number} pos_y - World-space Y position of the top-left corner of the overview
	 * @property {number} scale - Scale of the overview, e.g., 4 means 1 pixel of the overview equals 1 world-space unit.
	 */

	const db = window.db;
	const THREE = window.require('three');
	const fs = window.require('fs');
	const dialog = remote.require('dialog');
	const OverviewMesh = require('js/web/overview-mesh.js');
77

	/**
	 * Convert tick to milliseconds
	 * @param {number} tick - number of ticks
	 * @param {number} tickRate - ticks per second
	 * @returns {number} milliseconds
	 */
	function tickToMsecs(tick, tickRate) {
		return tick * 1000 / tickRate;
	}

	/**
	 * Convert milliseconds to tick count
	 * @param {number} msecs - time in milliseconds
	 * @param {number} tickRate - ticks per second
	 * @returns {number} ticks
	 */
	function msecsToTick(msecs, tickRate) {
		return msecs * tickRate / 1000;
	}

	export default {
		replace: false,
		props: {
			title: {
				required: true,
				twoWay: true
			},
            tempRoundStarts: [],
            clusterPositions: [],
            clusterWinRates: [], 
            clusterShapes: [],
            colorMap: {},
            highlightedCluster: {time: -1, index: -1},
		},
		data() {
			return {
				gameLevel: null,
				sessions: [],
				allEvents: [],
				events: [],
				overviewMesh: null,
				scene: null,
				camera: null,
				saveFrame: false,
				timeline: {
					items: [],
					groups: []
				},
                team:null,
			}
		},
		computed: {
			readyToVisualise() {
				return this.sessions.length > 0 && this.allEvents.length > 0 && this.events.length > 0;
			},
            selectedClusterGroup() {
                return $('#chkWinners').is(':checked') || $('#chkLosers').is(':checked');
            }
		},
		methods: {
			/**
			 * Broadcasts {@link event:updateFrame} to all children.
			 * @instance
			 * @memberof module:components/VisualisationTab
			 * @fires updateFrame
			 * @param {event:render} e
			 */
			render(e) {
				if (this.overviewData) {
					this.$broadcast(
						'updateFrame',
						Object.assign({}, e, {
							overviewData: this.overviewData
						})
					);
                    this.updatePopup();
				}
			},

			/**
			 * Creates an overview quad and positions the camera.
			 * @instance
			 * @memberof module:components/VisualisationTab
			 */
			loadOverview() {
				this.overviewData = window.require(`./overviews/${this.gameLevel.game}/${this.gameLevel.level}.json`);

				// remove the existing mesh
				if (this.overviewMesh) {
					this.scene.remove(this.overviewMesh);
				}

				let loader = new THREE.TextureLoader();

				let overviewTexture = loader.load(`overviews/${this.gameLevel.game}/${this.gameLevel.level}.png`);
				let material = new THREE.MeshBasicMaterial({map: overviewTexture, depthWrite: false});

				this.overviewMesh = new OverviewMesh(this.overviewData, material);
				this.scene.add(this.overviewMesh);

				this.camera.left = this.overviewData.pos_x;
				this.camera.top = this.overviewData.pos_y;
				this.camera.right = this.overviewData.pos_x + (1024 * this.overviewData.scale);
				this.camera.bottom = this.overviewData.pos_y - (1024 * this.overviewData.scale);
				this.camera.updateProjectionMatrix();
			},
            
            /**
			 * Loads clustering data for this map.
			 * @instance
			 * @memberof module:components/VisualisationTab
			 */
			loadClusters() {
                try {
                    this.clusterWinRates = window.require(`./data/${this.gameLevel.game}/${this.gameLevel.level}/clusterWinRates.json`);
                    this.clusterShapes = window.require(`./data/${this.gameLevel.game}/${this.gameLevel.level}/clusterShapes.json`);
                }
                catch(err) {
                    this.clusterWinRates = undefined;
                    this.clusterShapes = undefined;
                    console.log(err.message);
                }
                
                this.setupClusterOptions();
                this.colorMap = {}; //reset colour map
                $('#clusterColorTable').hide(); //hide colour map table
                $('.clusterColorRow').remove(); //remove rows of old colours
			},
            
            setupClusterOptions(){
                //remove any existing buttons
                $('.clusterButtons').remove();
            
                if (this.clusterShapes) {
                    //Get property labels
                    labels = this.clusterShapes.labels
                    for (var i =0; i<labels.length; i++) {
                        $("#clustersLabel").after('<div class="btn-group col-sm-8 clusterButtons" style="clear:both" id="clusterButtonGroup' + i + '" data-toggle="buttons">');
                        var buttonGroup = $('#clusterButtonGroup' + i);
                        for (var j =0; j<labels[i].length; j++) {
                            $(buttonGroup).append('<label class="btn btn-primary"><input type="checkbox" class="clusterButton" id="chkCluster' + labels[i][j] + '">' + labels[i][j] + '</label>');

                        }
                    }
                }

            },
            
            updatePopup() {
            
            },

			/**
			 * Adds items and groups to the timeline.
			 * @instance
			 * @memberof module:components/VisualisationTab
			 */
			visualiseTimeline() {
				this.timeline.items = this.sessions.map((session, index) => {
					return {
						session,
						id: -index,
						content: 'Time range',
						group: session.record.id,
						start: tickToMsecs(session.tickRange[0], session.record.tickrate),
						end: tickToMsecs(session.tickRange[1], session.record.tickrate)
					}
				});

				this.timeline.groups = this.sessions.map(session => {
					return {
						id: session.record.id,
						content: session.record.title,
						style: `background-color: ${session.colour}`
					}
				});

				let eventNames = this.events.filter(e => e.type.name == 'timeline').map(e => e.record.name);

				// if there are no events to visualise, nothing to query
				if (eventNames.length === 0) {
					return;
				}

				let queryString = `SELECT * FROM events WHERE events.name IN (:eventNames) AND events.session_id IN (:sessionIds)`;

				db.query(queryString, {
						type: db.QueryTypes.SELECT,
						replacements: {
							eventNames,
							sessionIds: this.sessions.map(s => s.record.id),
						}
					})
					.then(results => {
						this.timeline.items = this.timeline.items.concat(results.map(row => {
							let session = this.sessions.find(s => s.record.id == row.session_id)

							return {
								id: row.id,
								content: row.name,
								group: row.session_id,
								editable: false,
								start: tickToMsecs(row.tick, session.record.tickrate)
							}
						}));
					})
					.catch(err => this.$dispatch('error', err));
			},

			/**
			 * Called by UI when "Visualise" button is clicked to trigger visualisation components to run.
			 * @instance
			 * @memberof module:components/VisualisationTab
			 * @fires visualise
			 */
			visualise() {
                //if we are playing, stop this
                if (this.$refs.timeline.playing) {
                    this.stop();
                }
				this.visualiseTimeline();
				this.$broadcast('visualise', {overviewData: this.overviewData});
			},

			/**
			 * Store a snapshot at the next {@link event:postrender}
			 * @instance
			 * @memberof module:components/VisualisationTab
			 */
			save() {
				this.saveFrame = true;
			},
            playback(items) {
            
                var timePeriod = parseInt($('#timePeriodSlider').val());
            
                startInMsecs = this.$refs.timeline.timeline.getCustomTime("playbackTimeStart").getTime() + (timePeriod / 10);
                endInMsecs = this.$refs.timeline.timeline.getCustomTime("playbackTimeEnd").getTime() + (timePeriod / 10); //add 1 sec worth of data
                //set verticalbar time
                this.$refs.timeline.timeline.setCustomTime(new Date(startInMsecs), "playbackTimeStart");
                this.$refs.timeline.timeline.setCustomTime(new Date(endInMsecs), "playbackTimeEnd");
                    

                
                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    /*
                    startInTicks = msecsToTick(item.start, item.session.record.tickrate) + (item.session.record.tickrate * 6); 
                    endInTicks = msecsToTick(item.end, item.session.record.tickrate) + (item.session.record.tickrate * 6);

                    item.start = tickToMsecs(startInTicks, item.session.record.tickrate);
                    item.end = tickToMsecs(endInTicks, item.session.record.tickrate);
                    */
                    
                        
                    item.session.tickRange = [
                        msecsToTick(startInMsecs, item.session.record.tickrate),
                        msecsToTick(endInMsecs, item.session.record.tickrate)
                    ];
                    /*
                    item.session.tickRange = [
                        startInTicks,
                        endInTicks
                    ];*/

                    /*
                    add check for either a pause or a stop, add configuration to select time window, 
                    indicate playing on timeline somehow, either by moving bar on timeline or having an arrow
                    */                

                    if ((i == items.length - 1)  && this.$refs.timeline.playing) { 
                        var that = this;
                        setTimeout(function(){
                            that.playback(items);
                        }, 100);
                    }
                    
                    this.drawClusters();
                }
            },
            drawMousePosition(positions){
                var faCache = require('js/web/font-awesome-cache');//all this stuff is in the wrong place right now. this stuff is too low levelfor visualisation tab
                
                //clear previous mouse position marker
                var mouseMarker = this.scene.getObjectByName("mousePos");
                if (mouseMarker) {
                    this.scene.remove(mouseMarker);
                }
                
                var canvas = document.createElement('canvas');
                canvas.width = canvas.height = 64;

                // render the icon to a 2D canvas
                var ctx = canvas.getContext('2d');
                ctx.font = '32px FontAwesome';
                ctx.textBaseline = 'top';
                ctx.fillStyle = 'white';
                ctx.fillText(faCache.get('fa-circle'), 0, 0);
                
                let texture = new THREE.Texture(canvas);
				texture.needsUpdate = true;

                let material = new THREE.ShaderMaterial({
                    uniforms: {
                        useTexture: {type: 'i', value: 1},
                        texture1: {type: 't', value: texture},
                        colour: {type: 'c', value: new THREE.Color()},
                        minTick: {type: 'f', value: 0},
                        maxTick: {type: 'f', value: 1},
                        fadeOld: {type: 'i', value: 0},
                        opacityScalar: {type: 'f', value: 1},
                    },
                    vertexShader: fs.readFileSync('shaders/OverviewPoint.vert', 'utf8'),
                    fragmentShader: fs.readFileSync('shaders/OverviewPoint.frag', 'utf8'),
                    transparent: true,
                    depthTest: false
                });

                let geometry = new THREE.Geometry();

                let pos = {x: positions.x, y: positions.y, z:320};
                geometry.merge(
                    new THREE.PlaneGeometry(64, 64),
                    new THREE.Matrix4().makeTranslation(pos.x + 16, pos.y - 16, pos.z) //adjustments of 48px are to make circle appear in middle of click
                );

                let bufferGeometry = new THREE.BufferGeometry();
                bufferGeometry.fromGeometry(geometry);

                let mesh = new THREE.Mesh(bufferGeometry, material);
                mesh.renderOrder = this.renderOrder;
                mesh.visible = this.visible;
                mesh.name = "mousePos";
                
                this.scene.add(mesh);
            },
            showGauge(time,clusterNo) {
            //show gauge and if it isn't currently showing correct time/clusterid, redraw it
            //(gauge div always follows mouse regardless of being shown or not)
            
                if (this.tempRoundStarts.length > 0) {

                    //if less than certain distance, assume to be part of same cluster
                    //check that this isn't an outlier
                    //TODO: what if closest to outlier, but this would pull outlier into a cluster?
                    //TODO: Another option? Track all posiitons that this is within distance of and find mode/mean cluster that is connected?

                    if (typeof time !== 'undefined' && typeof clusterNo !== 'undefined') {
                        var winPercent = this.clusterWinRates[this.team][time][clusterNo].toFixed(1);
                        this.$refs.gauge.displayGauge(winPercent);
                        //window.alert("Win % chance: " + winPercent );
                    } else {
                        this.$refs.gauge.displayGauge(null);
                        //window.alert("Outlier. Unable to calculate win likelihood");
                    }

                }
            
                $('#gaugeDiv').css('display', 'block');
            },
            hideGauge(){
                $('#gaugeDiv').css('display', 'none');
            },
            clearClusters() {
                //clear previous cluster overlay
                var clusterOverlay = this.scene.getObjectByName("clusterOverlay");
                while (clusterOverlay) {
                    this.scene.remove(clusterOverlay);
                    clusterOverlay = this.scene.getObjectByName("clusterOverlay");
                }
            },
            
            getClusterShapes(listOfAttributes, unexploredAttributes){
                if (unexploredAttributes.length > 0 && unexploredAttributes[0].length > 0) {
                    for (var i = 0, count = unexploredAttributes[0].length; i < count; i++){
                        var newList = JSON.parse(JSON.stringify(listOfAttributes));
                        var nextAttribute = unexploredAttributes[0][i];
                        newList.push(nextAttribute);
                        this.getClusterShapes(newList, unexploredAttributes.slice(1));
                    }
                } else {
                    if (listOfAttributes.length > 0) {
                        var shapes = this.clusterShapes[listOfAttributes[0]];
                        for (var j=1; j < listOfAttributes.length; j++) {
                            shapes = shapes[listOfAttributes[j]];
                        }
                        var time = this.getNearestTick();
                        shapes = shapes[time]; //TODO: temp get relative time from positions passed from visTab
                        this.drawClusterShapes(time, shapes, this.getClusterColor(listOfAttributes), listOfAttributes);
                    }
                    
                }
                
            },
            
            getClusterColor(attributes){
                if (!(attributes in this.colorMap)){
                    var colors = ['red', 'green', 'yellow', 'aqua', 'purple', 'orange','pink'];
                    this.colorMap[attributes] = colors[Object.keys(this.colorMap).length];
                    
                    $("#clusterColorTable").append("<tr class='clusterColorRow'><td>" + attributes + "</td><td><table style='background:" + this.colorMap[attributes] + ";height:10px;width:10px'></table></tr>");
                    
                    if (Object.keys(this.colorMap).length == 1) {
                        $('#clusterColorTable').show();
                    }
                    
                }
                return this.colorMap[attributes];
            },

            
            drawClusters() {
                
                this.clearClusters();
                
                //build up list of each hierachy of things and then loop them adding cluster shapes to canvas
                var listOfButtons = $('.clusterButton')
                
                for (var i = 0; i < listOfButtons.length; i++) {
                    if ($(listOfButtons[i]).is(':checked')){
                    
                    }
                }
                
                var labels = this.clusterShapes['labels'];
                var time = this.getNearestTick();
                var clusterGroups = [];
                
                for (var i = 0; i < labels.length; i++) {
                    clusterGroups.push([]);
                    for (var j = 0; j < labels[i].length; j++) {
                        if ($('#chkCluster' + labels[i][j]).is(':checked')){
                            clusterGroups[i].push(labels[i][j]);
                        }
                        
                    }
                }
                
                this.getClusterShapes([],clusterGroups);
                
                
            },
            
            drawClusterShapes(time, clusterShapes, colorName, attributes){
                
                
                for (var i = 0;i< Object.keys(clusterShapes).length;i++) {
                    var clusterConvexHull = new THREE.Shape();
                    var x = clusterShapes[i][0][0];
                    var y = clusterShapes[i][0][1]; 
                    clusterConvexHull.moveTo(x,y);
                    for (var j = 1; j<Object.keys(clusterShapes[i]).length; j++){
                        var x = clusterShapes[i][j][0];
                        var y = clusterShapes[i][j][1];
                        clusterConvexHull.lineTo(x, y);
                        
                    }
                    var x = clusterShapes[i][0][0];
                    var y = clusterShapes[i][0][1]; 
                    clusterConvexHull.lineTo(x,y);
                    var clusterGeometry = new THREE.ShapeGeometry(clusterConvexHull);
                    
                    if (this.highlightedCluster && this.highlightedCluster.time == time && this.highlightedCluster.index == i) {
                        var shapeColor = new THREE.Color("white");
                    } else {
                        var shapeColor = new THREE.Color(colorName);
                    }
                    
                    var clusterMaterial = new THREE.MeshBasicMaterial( { color: shapeColor, transparent: true, opacity: 0.5 } );
                    var clusterMesh = new THREE.Mesh( clusterGeometry, clusterMaterial );
                    clusterMesh.name = "clusterOverlay";
                    clusterMesh.userData = {'time': time, 'clusterNo': i, 'attributes': attributes }
                    this.scene.add( clusterMesh );
                    }
            },
            
            getNearestTick() {
                if (!this.tempRoundStarts){
                    let roundStartQueryString =     `SELECT tick
                                                    FROM events
                                                    WHERE events.name = 'round_start'
                                                    AND events.session_id IN (:sessionIds)
                                                    ORDER BY tick`;
          
                    db.query(roundStartQueryString, {
                                                    type: db.QueryTypes.SELECT,
                                                    replacements: {
                                                        sessionIds: this.sessions.map(s => s.record.id) //TODO: make this work for multiple sessions
                                                    }
                            })
                            .then((results) => {
                                this.tempRoundStarts = results;
                            })
                            .catch(err => this.$dispatch('error', err));

                }
            
                //find most recent roundStart
                //TODO: Make this work for multiple sessions and get tickRate from file (not not 128 hardcoded)
                var currentTick = msecsToTick(this.$refs.timeline.timeline.getCustomTime("playbackTimeEnd").getTime(), 128);
                var relativeTicks;
                
                if (this.tempRoundStarts){ 

                    for (var n = this.tempRoundStarts.length - 1; n >= 0; n--) {
                        if (this.tempRoundStarts[n].tick < currentTick) {
                            relativeTicks = currentTick - this.tempRoundStarts[n].tick;
                            break;
                        }
                    }

                    //import cluster data
                    if (!this.clusterShapes) {
                        this.loadClusters();
                    }

                    if (relativeTicks) {
                        if (relativeTicks < 256) { relativeTicks = 256; } //TODO:get data for 0 secs or explain why there isn't data at spawn

                        //find nearest multiple of 256 (2 seconds)
                        //TODO: make this work for different tick rates?
                        return Math.round(relativeTicks / 256) * 256;
                    } else {
                        throw("Cannot calculate relative time of game");
                    }
                }
            }
            

		},
		ready() {
			this.$watch('gameLevel', this.loadOverview.bind(this));
            this.$watch('gameLevel', this.loadClusters.bind(this));

			this.$refs.renderer.$on('render', this.render.bind(this));

			// we need to save on `postrender` otherwise the buffer is black
			this.$refs.renderer.$on('postrender', () => {
				if (!this.saveFrame) {
					return;
				}

				this.saveFrame = false;

				let data = this.$refs.renderer.toDataURL('image/png');

				dialog.showSaveDialog(remote.getCurrentWindow(), {
					title: 'Save visualisation',
					filters: [
						{name: 'PNG', extensions: ['png']},
					]
				}, filename => {
					if (!filename) {
						return;
					}

					// data is a data URI (base64 encoded)
					let b64 = data.replace(/^data:image\/png;base64,/, '');
					fs.writeFileSync(filename, b64, 'base64');
				});
			});

			this.$refs.timeline.$on('moving', (item, cb) => {
				// update the tick range for this session, if we are not playing/paused
                if (!this.$refs.timeline.playing && !this.$refs.timeline.paused) {
            
                    item.session.tickRange = [
                        msecsToTick(item.start, item.session.record.tickrate),
                        msecsToTick(item.end, item.session.record.tickrate)
                    ];

                    cb(item);
                }
                
			});
            
            this.$refs.timeline.$on('play', (items) => {
                console.log("play event picked up");
                //afaik we only ever have one item on timeline so I'm just going to use that for now
                //set the time period of the visualisation aggregation to 3 minutes
                
                var minTime = 1; //can't set position of custom time bar in timeline to 0 so we set it to 1 milisecond past.
                var firstTimePeriod = 5000; //5 minute time period
                var maxTime = 0;
                
                //find when playback should stop (end of longest file)
                for (var i = 0; i < items.length; i++) {
                    var item = items[i];
                    
                    if (maxTime < item.end) {
                        maxTime = item.end; 
                    }
                    
                    if (!this.$refs.timeline.paused) { //if we've stopped, we should restart from beginning
                        item.session.tickRange = [
                            msecsToTick(minTime, item.session.record.tickrate), 
                            msecsToTick(firstTimePeriod, item.session.record.tickrate)
                        ];
                    }
                }
                
                if (!this.$refs.timeline.paused) { //if we've stopped we also need to readd the vertical bars indicating the time period
                    this.$refs.timeline.timeline.addCustomTime(new Date(minTime), "playbackTimeStart");
                    this.$refs.timeline.timeline.addCustomTime(new Date(firstTimePeriod), "playbackTimeEnd");
                }
                
                this.playback(items);
			});
            
            this.$refs.timeline.$on('timechange', (customTime, items) => {
                console.log("timebarchange");
                if (customTime.id === "playbackTimeStart") {
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        item.session.tickRange = [
                            msecsToTick(customTime.time, item.session.record.tickrate), 
                            item.session.tickRange[1]
                        ];
                    }
                } else if (customTime.id === "playbackTimeEnd") {
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        item.session.tickRange = [
                            item.session.tickRange[0],
                            msecsToTick(customTime.time, item.session.record.tickrate)
                        ];
                        this.displayTime = msecsToTick(customTime.time, item.session.record.tickrate)
                    }
                }
                
                this.drawClusters();
                
                
            });
            
            this.$refs.timeline.$on('stop', (items) => {
                var that = this;
                //adding a timeout ensures we avoid errors in playback by making sure this is done after we have stopped recursive calls to playback
                setTimeout(function() {
                    //reset bars on timeline
                    for (var i = 0; i < items.length; i++) {
                        var item = items[i];
                        //set the range back to item.start/item.end
                        //TODO: This still isn't working correctly
                        item.session.tickRange = [
                            msecsToTick(item.start, item.session.record.tickrate),
                            msecsToTick(item.end, item.session.record.tickrate)
                        ];
                    }

                    //get rid of vertical bars
                    that.$refs.timeline.timeline.removeCustomTime("playbackTimeStart");
                    that.$refs.timeline.timeline.removeCustomTime("playbackTimeEnd");
                }, 100);
                
                this.clearClusters();
                
            });
            
            this.$refs.renderer.$on('mouseMove', (event) => {
                if (this.overviewData) {
                    //get ingame positions
                    this.$refs.renderer.mouseVector.x = this.overviewData.pos_x + (event.offsetX * this.overviewData.scale);
                    this.$refs.renderer.mouseVector.y = this.overviewData.pos_y - (event.offsetY * this.overviewData.scale); 
                    
                    //this.$refs.renderer.mouseVector.x = ( event.clientX / canvas.innerWidth ) * 2 - 1;
                    //this.$refs.renderer.mouseVector.y = - ( event.clientY / canvas.innerHeight ) * 2 + 1;
                    
                    

                }
            });
            
            this.$refs.renderer.$on('mouseClick', (event) => {
                
                if (this.overviewData) {
                
                

                    /*use event.offsetX and event.offsetY to
                    convert to in game coordinates and then pass this
                    to another component that uses the precomputed
                    cluster data to determine which cluster the click is in
                    and the win/death statistics*/

                    //get ingame positions
                    xPosition = this.overviewData.pos_x + (event.offsetX * this.overviewData.scale);
                    yPosition = this.overviewData.pos_y - (event.offsetY * this.overviewData.scale); 
                    console.log("click: "+ xPosition + ", " + yPosition);
                    
                    var time = this.getNearestTick();

                    var clusterShapes = this.clusterShapes["win"][2][time];
                    var smallestDist = Math.sqrt(Math.pow((1024 * this.overviewData.scale), 2) * 2) //sizeOfMap
                    var smallestI = -1;
                    var smallestJ = -1;
                    for (var i = 0;i< Object.keys(clusterShapes).length;i++) {
                        for (var j = 1; j<Object.keys(clusterShapes[i]).length; j++){
                            var x = clusterShapes[i][j][0];
                            var y = clusterShapes[i][j][1];

                            var thisDist = Math.sqrt(Math.pow((x - xPosition), 2) + Math.pow((y - yPosition), 2));
                            
                            if (thisDist < smallestDist) {
                                smallestDist = thisDist;
                                smallestI = i;
                            }
                            
                        }
                    }
                    
                    if (smallestDist < 80) { //less than some value
                        this.highlightedCluster = {time: time, index: smallestI};
                        this.drawClusters();
                    }
                    
                    
                        
                }
                
                
                
                
            });
		}
	}
    
    
</script>

<style lang="less" rel="stylesheet/less">
	@import "../less/variables.less";

	.app-row__main {
		display: flex;
		min-height: 100vh;

		> div {
			padding: 1em;
		}
	}

	.main-panel__sidebar {
		background-color: @gray-lighter;
		min-width: 400px;

		hr {
			border-top: solid 2px white;
		}
	}
</style>
