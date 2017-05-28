<template>
    <div class = "btn-group" style="float:left">
      <button type = "button" class="btn btn-default" @click="play" :disabled="!canPlay">Play</button>
      <button type = "button" class="btn btn-default" @click="pause" :disabled="!canPause">Pause</button>
      <button type = "button" class="btn btn-default" @click="stop" :disabled="!canStop">Stop</button>
    </div>
    <div style="height:50px;width:200px;margin-left:250px;padding-top:10px;">
      <input type="range" id="timePeriodSlider" value="10000" min ="2000" max="20000" step ="2000" />
    </div>
	<div class="timeline" v-el:timeline></div>
</template>

<script type="text/babel">
	/**
	 * Component for displaying a Vis.js timeline.
	 * See vis.js documentation for info on items and groups.
	 * @module components/Timeline
	 *
	 * @param {object[]} items
	 * @param {object[]} groups
	 */

	const vis = window.require('./dist/components/vis/dist/vis');
    const rangeslider =  window.require('rangeslider.js');

	export default {
		props: {
			items: {
				required: true
			},
			groups: {}
		},
		data() {
			return {
				timeline: null,
                playing: false,
                paused: false
			}
		},
        computed: {
			canPlay() {
				return !this.playing;
			},
            canPause() {
				return this.playing;
			},
            canStop() {
				return this.playing || this.paused;
			},
		},
        methods: {
            play() {
                this.playing = true;
                
                this.$emit.bind(this, 'play')(this.items);
                
                if (this.paused == true) {
                    this.paused = false; //set this after we've sent out the "play" request so we know we were paused
                }
            },
            pause() {
                this.paused = true;
                this.playing = false;
            },
            stop() {
                this.playing = false;
                this.paused = false;
                this.$emit.bind(this, 'stop')(this.items);
            }
        },
		ready() {
            var timelimeComponent = this;
            
			this.$watch('items', () => this.timeline.setItems(this.items));
			this.$watch('groups', () => this.timeline.setGroups(this.groups));

			var options = {
				format: {
					minorLabels: {
						millisecond: 'SSS[ms]',
						second: 'HH:mm:ss',
						minute: 'HH:mm',
						hour: 'HH:mm',
					},
					majorLabels: {
						millisecond: 'HH:mm:ss',
						second: 'HH:mm',
						minute: 'HH [hours]',
						hour: '',
						weekday: '',
						day: '',
						month: '',
						year: ''
					}
				},
				min: 0, // msec
				max: 1000 * 60 * 60 * 2, // msec
				maxHeight: 300,
				stack: false,
				editable: {
					add: false,
					updateTime: true,
					updateGroup: false,
					remove: false
				},
				onMoving: this.$emit.bind(this, 'moving'),
				snap: null
			};

			this.timeline = new vis.Timeline(this.$els.timeline, this.items, options);
			this.timeline.setGroups(this.groups);
            this.timeline.on('timechange', function (id) { timelimeComponent.$emit.bind(timelimeComponent, 'timechange')(id, timelimeComponent.items);}) ;
            globalTimeline = this.timeline;
            
            $('#timePeriodSlider').rangeslider({polyfill : false});
		}
	}
</script>

<style lang="less" rel="stylesheet/less">
	.timeline {
		width: 1024px;
	}
</style>
