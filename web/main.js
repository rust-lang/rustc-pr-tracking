function parse_csv(raw) {
    var result = [];

    var lines = raw.split("\n");
    for (var i = 0; i < lines.length; i++) {
        result.push(lines[i].split(","));
    }

    return result;
}


function update_chart() {
    var req = new XMLHttpRequest();
    req.open("GET", "data/pr-status.csv", true);
    req.onreadystatechange = function() {
        if (req.readyState == XMLHttpRequest.DONE && req.status == 200) {
            process_data(req.responseText);
        }
    };
    req.send();
}


function process_data(data) {
    var csv = parse_csv(data);
    var data = {
        labels: [],
        datasets: [],
    };

    var random_colors = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6"];
    var max_days = 30;

    // First of all create all the new datasets
    for (var i = 1; i < csv[0].length; i++) {
        data.datasets.push({
            label: csv[0][i],
            data: [],
            backgroundColor: random_colors[i - 1],
        });
    }

    // Then load all the days
    for (var i = Math.min(max_days, csv.length - 1); i >= 1; i--) {
        data.labels.push(csv[i][0]);

        for (var j = 1; j < csv[i].length; j++) {
            data.datasets[j - 1].data.push(csv[i][j]);
        }
    }

    var ctx = document.getElementById("chart").getContext('2d');
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
            }
        }
    });
}


update_chart();
