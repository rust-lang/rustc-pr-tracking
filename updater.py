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

import csv
import datetime
import json
import os
import string
import subprocess
import sys
import time

import requests


API_URL = "https://api.github.com/search/issues"
REPOSITORY = "rust-lang/rust"


# GitHub doesn't support relative dates on `created:` and `updated:`, so this
# allows the CSV files to use `{param:relative-date}`
class QueryFormatter(string.Formatter):
    def format_field(self, value, format_spec):
        if format_spec == "relative-date":
            # Support date ranges
            if ".." in value:
                start, end = value.split("..", 1)

                return "%s..%s" % (
                    self.format_relative_date(start),
                    self.format_relative_date(end),
                )
            else:
                # Properly handle comparison operators
                cmp = ""
                for op in ">", ">=", "<", "<=":
                    if value.startswith(op):
                        cmp = op
                        value = value[len(op):]
                        break

                return cmp+self.format_relative_date(value)
        else:
            return super().format_field(value, format_spec)

    def format_relative_date(self, date):
        return str(datetime.date.today() - datetime.timedelta(days=int(date)))


def get_issues_count(http_session, query, param):
    """Get the number of issues with the provided label"""
    query = "is:pr is:open repo:{repo} {query}".format(
        repo=REPOSITORY,
        query=QueryFormatter().format(query, param=param),
    )

    while True:
        res = http_session.get(API_URL, params={"q": query})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait))
            time.sleep(wait)
            continue

        data = res.json()
        if "errors" in data:
            for error in data["errors"]:
                print("Error while searching for '%s': %s" % (query, error["message"]))
            exit(1)
        else:
            return data["total_count"]


def update_csv_file(http_session, path):
    """Add today's records to the provided csv file"""
    today = str(datetime.date.today())

    # Load the CSV file in memory
    with open(path) as f:
        content = list(csv.reader(f))

    # If today already has its own row don't add another one
    if len(content) == 1 or content[1][0] != today:
        content.insert(1, None)
    content[1] = [today]

    query = content[0][0]
    for param in content[0][1:]:
        content[1].append(str(get_issues_count(http_session, query, param)))

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

    # If a list of files to update isn't provided through args, update all the
    # .csv files in the `data/` directory
    files = sys.argv[1:]
    if not files:
        path = os.path.join(os.path.dirname(__file__), "data")

        for file in os.listdir(path):
            if file.endswith(".csv"):
                files.append(os.path.join(path, file))

    for file in files:
        update_csv_file(http_session, file)
