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

# pyright: strict

import csv
from datetime import datetime, timedelta, timezone
import os
import sys
import time
from typing import Callable
from urllib.parse import urlparse, parse_qs

import jinja2
import requests


API_URL = "https://api.github.com/search/issues"


# Various insignificant comments from triage, merge conflicts, etc 
# count as "updates" on GitHub, so `updated:` isn't a ideal way to
# gauge the last activity on a PR.
#
# Instead, use the Issue Events API to find when the
# status label (`S-*`) was most recently changed.
def get_pr_status_updated(http_session: requests.Session, repo: str, events_url: str, pr_number: int) -> str | None:
    """Get the timestamp of the last status label change for the given PR"""

    page = 1

    while True:
        print(f"Fetching events for {repo}#{pr_number}")
        res = http_session.get(events_url, params={"per_page": 100, "page": page})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait), flush=True)
            time.sleep(wait)
            continue

        # Make sure we got the last page
        # 
        # In most cases, the `per_page` of 100 should avoid
        # needing to issue another request.
        last = res.links.get("last")
        if last is not None and "url" in last:
            parsed = urlparse(last["url"])
            parsed_query = parse_qs(parsed.query)
            last_page = int(parsed_query["page"][0])

            if last_page > page:
                page = last_page
                continue

        data = res.json()
        print(data)
        if "errors" in data:
            for error in data["errors"]:
                print("Error while fetching events for '%s': %s" % (f"{repo}#{pr_number}", error["message"]))
            exit(1)
        else:
            break
    
    # Process events
    data = list(data) # data is a list of events

    # Find last 'labeled' event with label name 'S-*'
    for i, event in enumerate(reversed(data)):
        event_index = len(data) - i # because enumerating reversed

        if event["event"] == "labeled":
            label = str(event["label"]["name"])
            if label.startswith("S-"):
                # Continue iterating backwards to see if this label was the last one removed
                found_prev_event = False
                for prev_event in reversed(data[:event_index]):
                    if prev_event["event"] == "unlabeled":
                        prev_label = str(prev_event["label"]["name"])
                        if prev_label == label:
                            found_prev_event = True
                            break
                        elif prev_label.startswith("-S"):
                            break

                if found_prev_event:
                    # Same label was just removed and added back, so keep searching
                    continue
                else:
                    return event["created_at"]
    
    return None


# Convert ">1" to `(0.0, 1.0 + epsilon)`
# Convert "7..4" to `(4.0, 7.0)`
# Convert "<30" to `(30.0 + epsilon, inf)`
def relative_date_to_range(param: str) -> Callable[[int], int]:
    """Get a lambda that returns whether or not the argument
    is within the relative date range"""

    if "|" in param:
        value = param.split("|")[0]
    else:
        value = param

    # Support date ranges
    if ".." in value:
        end, start = value.split("..", 1)
        end, start = int(end), int(start)

        return lambda x : (x >= start and x <= end)
    else:
        # Properly handle comparison operators
        if value.startswith(">"):
            value = value[len(">"):]
            value = int(value)
            return lambda x : (x < value)
        if value.startswith(">="):
            value = value[len(">="):]
            value = int(value)
            return lambda x : (x <= value)
        if value.startswith("<"):
            value = value[len("<"):]
            value = int(value)
            return lambda x : (x > value)
        if value.startswith("<="):
            value = value[len("<="):]
            value = int(value)
            return lambda x : (x >= value)

        value = int(value)
        return lambda x : (x == value)


def status_updated(http_session: requests.Session, now: datetime, repo: str, query: str, params: list[str]):
    """Fetch the time the status was last updated for each PR,
    and compile into a histogram with bins defined by params"""

    # `__status_updated:` must come last in the query
    query = query.split("__status_updated:{{param|relative_date}}", 1)[0]
    query = f"is:pr repo:{repo} {query}".strip()

    bin_ranges = [relative_date_to_range(param) for param in params]
    bins = [0 for _ in params]

    # Iterate through list of all PRs
    page = 1
    last_page = 1

    while page <= last_page:
        print(f"Querying {query}", flush=True)
        res = http_session.get(API_URL, params={"q": query, "per_page": 100, "page": page})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait), flush=True)
            time.sleep(wait)
            continue

        data = res.json()
        print(data)
        if "errors" in data:
            for error in data["errors"]:
                print("Error while searching for '%s': %s" % (query, error["message"]))
            exit(1)

        # Calculate last page
        last_page = int(data["total_count"]) / 100

        # Process each PR
        for pr in data["items"]:
            pr_number = int(pr["number"])
            updated = get_pr_status_updated(http_session, repo, pr["events_url"], pr_number)

            if updated is None:
                updated = str(pr["updated_at"])
                print(f"{repo}#{pr_number} status updated not found, using updated field instead: {updated}")
            else:
                print(f"{repo}#{pr_number} last updated at {updated}")
            
            # Correct for older pythons
            updated = updated.replace("Z", "+00:00")

            # Get the relative time period
            diff = now.date() - datetime.fromisoformat(updated).date()

            print(f"{repo}#{pr_number} not updated in {diff.days} days")

            # Increment the bin that this diff fits in
            for i, r in enumerate(bin_ranges):
                if r(diff.days):
                    param = params[i]
                    print(f"{repo}#{pr_number} added to bin #{i} for '{param}'")
                    bins[i] += 1
                    break
        
        page += 1
        
    return bins


# GitHub doesn't support relative dates on `created:` and `updated:`, so this
# allows the CSV files to use `{{param|relative_date}}`
def filter_relative_date(now: datetime, value: str):
    def format_relative_date(date: str):
        return str(now.date() - timedelta(days=int(date))) + "T00:00:00+00:00"

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


def get_issues_count(http_session: requests.Session, repo: str, jinja_env: jinja2.Environment, query: str, param: str):
    """Get the number of issues with the provided label"""
    # Strip pretty labels from the query
    if "|" in param:
        param = param.split("|")[0]

    query_tmpl = jinja_env.from_string(query)
    query = "is:pr repo:{repo} {query}".format(
        repo=repo,
        query=query_tmpl.render(param=param),
    )

    while True:
        print(f"Querying {query}")
        res = http_session.get(API_URL, params={"q": query})

        # Properly handle rate limits
        if res.status_code == 403:
            wait = float(res.headers["X-RateLimit-Reset"]) - time.time() + 1
            print("Rate limit reached, waiting %s seconds..." % int(wait), flush=True)
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


def update_csv_file(http_session: requests.Session, repo: str, path: str):
    """Add today's records to the provided csv file"""
    now = datetime.now(tz=timezone.utc)
    today = str(now.date())

    # Load the CSV file in memory
    with open(path) as f:
        content = list(csv.reader(f))

    # If today already has its own row don't add another one
    if len(content) == 1 or content[1][0] != today:
        content.insert(1, [])
    content[1] = [today]

    # Setup the Jinja2 environment
    jinja_env = jinja2.Environment()
    jinja_env.filters["relative_date"] = lambda value : filter_relative_date(now, str(value)) # type: ignore

    query = content[0][0]

    # Custom query requring custom logic
    if "__status_updated:{{param|relative_date}}" in query:
        for bin in status_updated(http_session, now, repo, query, content[0][1:]):
            content[1].append(str(bin))
    else:
        for param in content[0][1:]:
            content[1].append(str(get_issues_count(http_session, repo, jinja_env, query, param)))

    with open(path, "w") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(content)


if __name__ == "__main__":
    http_session = requests.Session()
    http_session.headers["Accept"] = "application/vnd.github+json"
    http_session.headers["X-GitHub-Api-Version"] = "2022-11-28"

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
