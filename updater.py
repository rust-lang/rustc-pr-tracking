#!/usr/bin/env python3
# Copyright (c) 2018 Pietro Albini <pietro@pietroalbini.org>
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
import subprocess
import time

import requests


API_URL = "https://api.github.com/search/issues"

DATA_FILE = "data/pr-status.csv"

REPOSITORY = "rust-lang/rust"


def get_issues_count(http_session, label):
    """Get the number of issues with the provided label"""
    query = "is:pr is:open label:%s repo:%s" % (label, REPOSITORY)

    while True:
        res = http_session.get(API_URL, params={"q": query})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait))
            time.sleep(wait)
            continue

        return res.json()["total_count"]


def update_csv_file(http_session, path):
    """Add today's records to the provided csv file"""
    today = str(datetime.date.today())

    # Load the CSV file in memory
    with open(path) as f:
        content = list(csv.reader(f))

    # If today already has its own row don't add another one
    if content[1][0] != today:
        content.insert(1, None)
    content[1] = [today]

    for label in content[0][1:]:
        content[1].append(str(get_issues_count(http_session, label)))

    with open(path, "w") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(content)


if __name__ == "__main__":
    update_csv_file(requests.Session(), DATA_FILE)
