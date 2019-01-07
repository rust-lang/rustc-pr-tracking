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


var raw_data = {};
var last_update = {};


function parse_csv(raw) {
    var result = [];

    var lines = raw.split("\n");
    for (var i = 0; i < lines.length; i++) {
        result.push(lines[i].split(","));
    }

    return result;
}


function fetch_graphs() {
    var graphs = document.querySelectorAll("div.graph");
    for (var i = 0; i < graphs.length; i++) {
        var graph = graphs[i];

        var req = new XMLHttpRequest();
        var url = "data/" + graph.id + ".csv";
        req.open("GET", url, true);
        req.onreadystatechange = function() {
            if (this.req.readyState == XMLHttpRequest.DONE && this.req.status == 200) {
                raw_data[this.graph.id] = this.req.responseText;
                process_data(this.graph);
            }
        }.bind({req: req, graph, graph});
        req.send();
    }
}


function update_graphs() {
    var graphs = document.querySelectorAll("div.graph");
    for (var i = 0; i < graphs.length; i++) {
        process_data(graphs[i]);
    }
}


function process_data(graph) {
    var csv = parse_csv(raw_data[graph.id]);
    var data = {
        labels: [],
        datasets: [],
    };

    var random_colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#66aa00", "#dd4477"];
    var max_days = document.getElementById("days-count").value;
    var relative = document.getElementById("relative").checked;

    var state = [max_days, relative];

    if (graph.id in last_update && state == last_update[graph.id]) {
        return;
    } else {
        last_update[graph.id] = state;
    }

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

            if (relative === true) {
                var sum = 0;

                for (var j = 1; j < csv[i].length; j++) {
                    sum += parseInt(csv[i][j]);
                }
                for (var j = 1; j < csv[i].length; j++) {
                    data.datasets[j - 1].data.push(Math.round((csv[i][j] * 100 / sum) * 100) / 100);
                }
            } else {
                for (var j = 1; j < csv[i].length; j++) {
                    data.datasets[j - 1].data.push(csv[i][j]);
                }
            }
        }
    }

    var canvas = graph.getElementsByTagName("canvas")[0];
    canvas.parentElement.appendChild(document.createElement("canvas"));
    canvas.parentElement.removeChild(canvas);

    var canvas = graph.getElementsByTagName("canvas")[0];
    var ctx = canvas.getContext('2d');
    new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            animation: false,
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
                    label: function(item) {
                        var label = data.datasets[item.datasetIndex].label + ':  ' + item.yLabel;
                        if (relative) {
                            return label + '%';
                        } else {
                            return label;
                        }
                    },
                    footer: function(items) {
                        if (!relative) {
                            var sum = 0;
                            for (var i = 0; i < items.length; i++) {
                                sum += items[i].yLabel;
                            }

                            return 'Total PRs:  ' + sum;
                        }
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
fetch_graphs();


document.getElementById("days-count").addEventListener("keydown", function(e) {
    if (e.keyCode == 13) {
        update_graphs();
    }
})

document.getElementById("days-count").addEventListener("focusout", function() {
    if (this.value === "") {
        this.value = "30";
    }

    update_graphs();
})

document.getElementById("relative").addEventListener("input", function(e) {
    update_graphs();
})
