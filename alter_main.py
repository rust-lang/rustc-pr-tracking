import requests
import csv
import os
import datetime

GITHUB_API_URL = "https://api.github.com"
GITHUB_SEARCH_ISSUES_API = "/search/issues"
CSV_DIRECTORY = "data"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

session = requests.Session()
if GITHUB_TOKEN:
    session.headers.update({"Authorization": f"token {GITHUB_TOKEN}"})

def get_issues_count(query):
    """Get the number of issues with the provided label"""
    url = f"{GITHUB_API_URL}{GITHUB_SEARCH_ISSUES_API}"
    params = {"q": query}
    response = session.get(url, params=params)
    data = response.json()
    if "errors" in data:
        print(f"Error while searching for '{query}': {data['errors'][0]['message']}")
        exit(1)
    return data["total_count"]

def update_csv_file(repo, path):
    """Add today's records to the provided csv file"""
    today = str(datetime.date.today())

    with open(path, "r") as f:
        reader = csv.reader(f)
        content = list(reader)

    if len(content) == 1 or content[1][0] != today:
        content.insert(1, [today])

    for i in range(1, len(content[0])):
        query = content[0][i]
        param = content[1][0]
        count = get_issues_count(f"is:pr repo:{repo} {query}={param}")
        content[1][i] = count

    with open(path, "w") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerows(content)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: %s <repo> [files ...]" % sys.argv[0])
        exit(1)
    repo = sys.argv[1]

    if not GITHUB_TOKEN:
        print("Warning: the $GITHUB_TOKEN environment variable is not set!")
        print("The script will still work, but it might be rate limited.")

    # If a list of files to update isn't provided through args, update all the
    # .csv files in the `data/` directory
    files = sys.argv[2:]
    if not files:
        path = os.path.join(os.path.dirname(__file__), CSV_DIRECTORY, repo)
        for file in os.listdir(path):
            if file.endswith(".csv"):
                files.append(os.path.join(path, file))

    for file in files:
        update_csv_file(repo, file)
