import yaml
import argparse
import os
import logging
import re
import subprocess
import urllib.request
import json
import pygit2

from packaging import version

parser = argparse.ArgumentParser(description="Generate Atlassian based Dockerfiles")
parser.add_argument("--config", help="a YaML file with configuration (default: atlassian.yml)", default="atlassian.yml")
parser.add_argument("--workdir",
                    help="Location where the script should operate (default: work subdirectory)",
                    default=os.path.dirname(__file__) + "/work")
parser.add_argument("--sshagent",
                    help="Use the SSH-agent for authentication. "
                         "When False you need to provide the password to your private key. (default: True)",
                    default=True)
parser.add_argument("--sshpassword", help="Provide the password for your private key if not using the ssh-agent")

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

# Cache software feeds so we don't make multiple calls in one run
feeds = {}

# We only support key-based authentication
if args.sshagent:
    gitkeypair = pygit2.Keypair("git", None, None, "")
else:
    gitkeypair = pygit2.Keypair("git", "id_rsa.pub", "id_rsa", args.sshpassword)

gitcallbacks = pygit2.RemoteCallbacks(credentials=gitkeypair)


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

    if not os.path.exists(path):
        logging.info("Cloning to {}".format(path))

        # Clone the repository
        pygit2.clone_repository(application['repository'], path, callbacks=gitcallbacks)

    logging.info("Switching to master branch")
    repo = pygit2.Repository(path)
    repo.checkout("refs/heads/master")

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

