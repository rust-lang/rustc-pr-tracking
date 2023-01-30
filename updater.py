#!/usr/bin/env python3
# Copyright (c) 2018 The Rust Project Developers
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from pathlib import Path
import csv
import datetime
import json
import os
import subprocess
import sys
import time
import jinja2

import requests


API_URL = "https://api.github.com/search/issues"


# GitHub doesn't support relative dates on `created:` and `updated:`, so this
# allows the CSV files to use `{{param|relative_date}}`
def filter_relative_date(value):
    def format_relative_date(date):
        return str(datetime.date.today() - datetime.timedelta(days=int(date))) + "T00:00:00+00:00"

    # Support date ranges
    if ".." in value:
        start, end = value.split("..", 1)

        return "%s..%s" % (
            format_relative_date(start),
            format_relative_date(end),
        )
    else:
        # Properly handle comparison operators
        cmp = ""
        for op in ">", ">=", "<", "<=":
            if value.startswith(op):
                cmp = op
                value = value[len(op):]
                break

        return cmp+format_relative_date(value)


def get_issues_count(http_session, repo, jinja_env, query, param):
    """Get the number of issues with the provided label"""
    # Strip pretty labels from the query
    if "|" in param:
        param = param.split("|")[0]

    query_tmpl = jinja_env.from_string(query)
    query = "repo:{repo} {query}".format(
        repo=repo,
        query=query_tmpl.render(param=param),
    )

    while True:
        print(f"Querying {query}")
        res = http_session.get(API_URL, params={"q": query})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait))
            time.sleep(wait)
            continue

        data = res.json()
        print(data)
        if "errors" in data:
            for error in data["errors"]:
                print("Error while searching for '%s': %s" % (query, error["message"]))
            exit(1)
        else:
            return data["total_count"]


def update_csv_file(http_session, repo, path):
    """Add today's records to the provided csv file"""
    today = str(datetime.date.today())

    # Load the CSV file in memory
    with open(path) as f:
        content = list(csv.reader(f))

    # If today already has its own row don't add another one
    if len(content) == 1 or content[1][0] != today:
        content.insert(1, None)
    content[1] = [today]

    # Setup the Jinja2 environment
    jinja_env = jinja2.Environment()
    jinja_env.filters["relative_date"] = filter_relative_date

    issue_type = Path(path).name.split("-", 1)[0]
    query = content[0][0]
    query = f"is:{issue_type} {query}"
    for param in content[0][1:]:
        content[1].append(str(get_issues_count(http_session, repo, jinja_env, query, param)))

    with open(path, "w") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(content)


if __name__ == "__main__":
    http_session = requests.Session()

    if "GITHUB_TOKEN" in os.environ:
        http_session.auth = ('x-token', os.environ["GITHUB_TOKEN"])
    else:
        print("Warning: the $GITHUB_TOKEN environment variable is not set!")
        print("The script will still work, but it might be rate limited.")

    if len(sys.argv) < 2:
        print("usage: %s <repo> [files ...]" % sys.argv[0])
        exit(1)
    repo = sys.argv[1]

    # If a list of files to update isn't provided through args, update all the
    # .csv files in the `data/` directory
    files = sys.argv[2:]
    if not files:
        path = os.path.join(os.path.dirname(__file__), "data", repo)

        for file in os.listdir(path):
            if file.endswith(".csv"):
                files.append(os.path.join(path, file))

    for file in files:
        update_csv_file(http_session, repo, file)
