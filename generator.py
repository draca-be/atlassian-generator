import yaml
import argparse
import os
import logging
import re
import subprocess
import urllib.request
import json

from packaging import version


parser = argparse.ArgumentParser(description="Generate Atlassian based Dockerfiles")
parser.add_argument("--config", help="a YaML file with configuration (default: atlassian.yml)", default="atlassian.yml")
parser.add_argument("--workdir", help="Location where the script should operate (default: work subdirectory)", default=os.path.dirname(__file__) + "/work")
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

# Cache software feeds so we don't make multiple calls in one run
feeds = {}


def git(args, path=''):
    if path != '':
        args = ['-C', path] + args

    subprocess.run(['git'] + args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def processversion(application, versioninfo, path):
    logging.info("  -> {}".format(versioninfo['version']))


def processapp(application):
    logging.info("Processing {}".format(application['name']))

    if 'repository' not in application:
        logging.warning("No repository configured, skipping")
        return

    # Extract directory name from repository
    m = re.match(r"[^/]*/(.*).git", application['repository'])
    path = os.path.join(args.workdir, m.group(1))

    if os.path.exists(path):
        logging.info("Repository checked out")

        # Make sure we are in master
        git(['checkout', 'master'], path)

    else:
        logging.info("Cloning to {}".format(path))

        # Clone the repository
        git(['clone', application['repository'], path])

    minimumversion = version.parse(application.get('minimumVersion', '0.0.1'))
    maximumversion = version.parse(application.get('maximumVersion', '999.999.999'))

    for feed in application['feeds']:
        # If we don't have a cached version, fetch the .json
        if feed not in feeds:
            with urllib.request.urlopen(feed) as url:
                feeddata = url.read().decode()
                feeds[feed] = json.loads(feeddata[10:-1])

        # Use the cached version
        feeddata = feeds[feed]

        # Iterate all the versions
        for versioninfo in feeddata:
            itemversion = version.parse(versioninfo['version'])

            # Only pick the tarballs and filter out versions
            if re.match(r".*TAR\.GZ Archive.*", versioninfo['description']) \
                    and versioninfo['type'] == 'Binary' \
                    and maximumversion >= itemversion >= minimumversion:
                # Process the app version
                processversion(application, versioninfo, path)


if __name__ == '__main__':
    with open(args.config, 'r') as stream:
        data = yaml.load(stream)

        for item in data:
            processapp(item)

