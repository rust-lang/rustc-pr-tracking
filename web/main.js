/*  Copyright (c) 2018 The Rust Project Developers
 *
 *  Permission is hereby granted, free of charge, to any person obtaining a copy
 *  of this software and associated documentation files (the "Software"), to deal
 *  in the Software without restriction, including without limitation the rights
 *  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 *  copies of the Software, and to permit persons to whom the Software is
 *  furnished to do so, subject to the following conditions:
 *
 *  The above copyright notice and this permission notice shall be included in
 *  all copies or substantial portions of the Software.
 *
 *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 *  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 *  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 *  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 *  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 *  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 *  SOFTWARE.
 */


function parse_csv(raw) {
    var result = [];

    var lines = raw.split("\n");
    for (var i = 0; i < lines.length; i++) {
        result.push(lines[i].split(","));
    }

    return result;
}


function update_graphs() {
    var graphs = document.querySelectorAll("div.graph");
    for (var i = 0; i < graphs.length; i++) {
        var graph = graphs[i];

        var req = new XMLHttpRequest();
        var url = "data/" + graph.id + ".csv";
        req.open("GET", url, true);
        req.onreadystatechange = function() {
            if (this.req.readyState == XMLHttpRequest.DONE && this.req.status == 200) {
                process_data(this.req.responseText, this.graph);
            }
        }.bind({req: req, graph, graph});
        req.send();
    }
}


function process_data(data, graph) {
    var csv = parse_csv(data);
    var data = {
        labels: [],
        datasets: [],
    };

    var random_colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#66aa00", "#dd4477"];
    var max_days = 30;

    // First of all create all the new datasets
    for (var i = 1; i < csv[0].length; i++) {
        // Strip param from nice labels
        var label = csv[0][i];
        if (label.indexOf("|") !== -1) {
            label = label.split("|", 2)[1];
        }

        data.datasets.push({
            label: label,
            data: [],
            backgroundColor: random_colors[(i - 1) % random_colors.length],
        });
    }

    // Then load all the days
    for (var i = max_days; i >= 1; i--) {
        if (i >= csv.length - 1) {
            data.labels.push("");

            for (var j = 0; j < data.datasets.length; j++) {
                data.datasets[j].data.push(0);
            }
        } else {
            data.labels.push(csv[i][0]);

            for (var j = 1; j < csv[i].length; j++) {
                data.datasets[j - 1].data.push(csv[i][j]);
            }
        }
    }

    var ctx = graph.getElementsByTagName("canvas")[0].getContext('2d');
    var myChart = new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero:true
                    },
                    stacked: true,
                }]
            },
            tooltips: {
                mode: 'index',
                intersect: false,
                multiKeyBackground: 'transparent',

                titleMarginBottom: 8,
                footerMarginTop: 12,
                footerFontStyle: 'normal',

                callbacks: {
                    footer: function(items) {
                        var sum = 0;
                        for (var i = 0; i < items.length; i++) {
                            sum += items[i].yLabel;
                        }

                        return 'Total PRs:  ' + sum;
                    },
                }
            }
        }
    });
}


function populate_toc() {
    var toc = document.getElementById("toc");

    var graphs = document.querySelectorAll(".graph");
    for (var i = 0; i < graphs.length; i++) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.classList.add("button");
        a.href = "#" + graphs[i].id;
        a.innerHTML = graphs[i].querySelector("h2").innerHTML;
        li.appendChild(a);
        toc.appendChild(li);
    }
}


populate_toc();
update_graphs();
