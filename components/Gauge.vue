<template>
	<div id="gauge" style="width:400px; height:320px; background:rgb(255,255,255)"></div>
</template>

<script type="text/babel">
	/**
	 * Component for displaying win rates as a gauge
	 * @module components/Gauge
	 */

    
	const justgage = window.require('justgage');
    const eve = window.require('eve');
    const Raphael = window.require('raphael');

	export default {
		replace: false,
		props: {
            gauge: null,
		},
        
		methods: {


			/**
			 * Remove all objects from the scene.
			 * @instance
			 * @memberof module:components/VisDiscontinuous
			 */
			clear() {

			},
            
            
            
            displayGauge(val) {
                //var Raphael = window.require('raphael');
                
                if (val == null) {
                    $("#gauge").css('visibility','hidden');
                    
                } else {
                    $("#gauge").css('visibility','visible');
                }
            
                if (!this.gauge) {
                    //setup gauge, then refresh its value as its number doesn't display properly on inialisation for some reason
                    this.gauge = new JustGage({
                        id: "gauge",
                        value: val,
                        min: 0,
                        max: 100,
                        title: "Win Rate",
                        decimals: 1,
                        pointer: true,
                        gaugeWidthScale: 0.6,
                        levelColors: ['#ff0000', '#00ff00'],
                      });
                
                } 
                this.gauge.refresh(val);

			},
		},
		/*events: {
			

		},
		ready() {

		},
		detached() {
			this.clear();
		}*/
	}
</script>
