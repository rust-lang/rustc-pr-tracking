# rustc's pull requests tracking

This repository tracks the status of rustc's PRs over time: historic data is
stored in it, and a bot adds new data every day.

The raw data is available in CSV format in the `data/` directory, and a [web
dashboard](https://pietroalbini.github.io/rustc-pr-tracking/) is available with
a chart.

## Adding new graphs

If you want to track data for a new graph, you need to create a new `.csv` file
in the `data` directory with just the first row. The first cell in that row is
the query you want to use (with `%s` as the placeholder), and in the other
cells the various strings that will replace `%s` in the query. For example,
this row counts how much PRs each of the listed labels has:

```
label:%s,S-waiting-on-review,S-waiting-on-author
```

If you also want to show a graph on the web dashboard, add this snippet to the
`index.html` file:

```
<div class="graph" data-url="data/your-file-name.csv">
    <h2>Your section title</h2>
    <canvas></canvas>
</div>
```

You can then run the updater script to populate today's data automatically.

## Running the updater script

The updater script requires Python 3 and git installed on the local machine,
and must be executed inside a clone of this repository. You can execute the
script simply with:

```
$ python3 updater.py
```

The script will automatically pull from the remote, update the data, commit it
with the bot details and push the new commit to the remote. It is released
under the MIT license.
