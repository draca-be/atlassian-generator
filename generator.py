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


def processversion(config, source, path):
    logging.info("  -> {}".format(source['version']))


def processapp(item):
    logging.info("Processing {}".format(item['name']))

    if 'repository' not in item:
        logging.warning("No repository configured, skipping")
        return

    m = re.match(r"[^/]*/(.*).git", item['repository'])
    path = os.path.join(args.workdir, m.group(1))

    if os.path.exists(path):
        logging.info("Repository checked out")
        git(['checkout', 'master'], path)
    else:
        logging.info("Cloning to {}".format(path))
        git(['clone', item['repository'], path])

    minimumversion = version.parse(item.get('minimumVersion', '0.0.1'))
    maximumversion = version.parse(item.get('maximumVersion', '999.999.999'))

    for feed in item['feeds']:
        if feed not in feeds:
            with urllib.request.urlopen(feed) as url:
                feeddata = url.read().decode()
                feeds[feed] = json.loads(feeddata[10:-1])

        feeddata = feeds[feed]

        for feeditem in feeddata:
            itemversion = version.parse(feeditem['version'])

            if re.match(r".*TAR\.GZ Archive.*", feeditem['description']) \
                    and feeditem['type'] == 'Binary' \
                    and maximumversion >= itemversion >= minimumversion:
                processversion(item, feeditem, path)


if __name__ == '__main__':
    with open(args.config, 'r') as stream:
        data = yaml.load(stream)

        print(data)

        for item in data:
            processapp(item)

