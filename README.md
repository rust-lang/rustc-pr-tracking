# Rustc PR tracking

This repository tracks the status of rustc's PRs over time: all the data is
available in the CSV format, and it's updated daily by a bot running on GitHub
Actions. A [Web dashboard](https://rust-lang.github.io/rustc-pr-tracking/) is
also available with graphs of the collected data.

The content of this repository is released under the MIT license.

## Adding new graphs

If you want to track data for a new graph, you need to create a new `.csv` file
in the `data` directory with just the first row. The first cell in that row is
the query you want to use (with `{{param}}` as the placeholder), and in the
other cells the various strings that will replace `{{param}}` in the query (the
query is actually a Jinja2 template). For example, this row counts how much PRs
each of the listed labels has:

```
label:{{param}},S-waiting-on-review,S-waiting-on-author
```

You can add pretty labels to each column by putting the label after `|`: this
way it's possible to hide hard-to-read query params. If you also want to show a
graph on the web dashboard, add the file name (without the `.csv`) and the
title you want for the graph to the `graphs` section of the `.md` file of the
dashboard you're interested in.

You can then run the updater script to populate today's data automatically.

### Adding new params to existing graphs

New params must be added to the end of the list.

```diff
- is:open label:{{param}},S-waiting-on-author,S-waiting-on-review
+ is:open label:{{param}},S-waiting-on-author,S-waiting-on-review,S-inactive
```

## Running the updater script locally

The updater script can also be run locally: you just need to have Python 3 and
the python-requests library installed.

```
# Update all the CSV files in the data/ directory
$ python3 updater.py <repo-name>

# Update just the data/sample.csv file
$ python3 updater.py <repo-name> data/sample.csv
```

If the `GITHUB_TOKEN` environment variable is present, the script will use it
to authenticate with the GitHub API: it can work fine without it, but the API
rate limits are pretty low for unauthenticated requests (don't worry, the
script will wait for the limits to expire, it will just take more time to
finish).

**Do not run** the `ci.sh` script: it's meant to be run by Travis, and it will
push new commits to this repository.
