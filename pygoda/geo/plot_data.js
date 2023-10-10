var createPlot = function(staname, stadata) {
    // low,high
    let data = [stadata.Zlow, stadata.Zhigh, stadata.Z];

    // let d = Date.UTC(2010,0,1)/1000;
    // let num = 365;

    data.unshift(stadata.t);

    function fmtUSD(val, dec) {
        return "$" + val.toFixed(dec).replace(/\d(?=(\d{3})+(?:\.|$))/g, '$&,');
    }

    const opts = {
        width: 400,
        height: 200,
        title: staname + " vertical component",
        // tzDate: ts => uPlot.tzDate(new Date(ts * 1e3), 'Etc/UTC'),
        scales: {
					  x: {
						    time: false,
					  }
        },
        series: [
            {},
            {
                label: "Low",
                stroke: "blue",
                fill: "rgba(0, 0, 0, .07)",
                value: (u, v) => v + " mm",
                band: true,
                width: 0,
                spanGaps: false
            },
            {
                label: "High",
                stroke: "red",
                fill: "rgba(0, 0, 0, .07)",
                value: (u, v) => v + " mm",
                band: true,
                width: 0,
                spanGaps: false
            },
            {
                label: "Avg",
                stroke: "teal",
                // dash: [10, 10],
                width: 1,
                value: (u, v) => v + " mm",
                spanGaps: false
            },
        ],
        axes: [
            {},
            {
                values: (u, vals) => vals.map(v => v + " mm")
            }
        ]
    };

    let plot = document.querySelector("#plot_" + staname);
    let u = new uPlot(opts, data, plot);
};

