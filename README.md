# rustc's pull requests tracking

This repository tracks the status of rustc's PRs over time: historic data is
stored in it, and a bot adds new data every day. You can find the data in the
`data/` directory.

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
