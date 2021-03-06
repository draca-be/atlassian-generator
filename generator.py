import shutil
import yaml
import argparse
import os
import logging
import re
import urllib.request
import json
import pygit2
import jinja2
import subprocess

from packaging import version

parser = argparse.ArgumentParser(description="Generate Atlassian based Dockerfiles")
parser.add_argument("--config", help="a YaML file with configuration (default: atlassian.yml)", default="atlassian.yml")
parser.add_argument("--repositories", help="a YaML file with repository configuration (default: repositories.yml)", default="repositories.yml")
parser.add_argument("--workdir",
                    help="Location where the script should operate (default: work subdirectory)",
                    default=os.path.join(os.path.dirname(__file__), 'work'))
parser.add_argument("--templatedir",
                    help="Location that contains all the templates (default: templates subdirectory)",
                    default=os.path.join(os.path.dirname(__file__), 'templates'))
parser.add_argument("--nosshagent",
                    help="Don't use SSH agent based authentication.",
                    action='store_true')
parser.add_argument("--sshpassword", help="Provide the password for your private key. Implies --nosshagent")
parser.add_argument("--commitname",
                    help="Name of the commit author (default: draca-be/atlassian-generator)",
                    default="draca-be/atlassian-generator")
parser.add_argument("--commitemail",
                    help="Email of the commit author (default: mathy@draca.be)",
                    default="mathy@draca.be")
parser.add_argument("--dontpush",
                    help="Don't push to the remote repository",
                    action='store_true')
parser.add_argument("templates", metavar="template", nargs="?",
                    help="Specify the template to parse (default: all)")

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

# Cache software feeds so we don't make multiple calls in one run
feeds = {}

# We only support key-based authentication
if args.sshpassword:
    gitkeypair = pygit2.Keypair("git", os.path.expanduser("~/.ssh/id_rsa.pub"), os.path.expanduser("~/.ssh/id_rsa"), args.sshpassword)

elif not args.nosshagent:
    if 'SSH_AUTH_SOCK' not in os.environ:
        logging.error("SSH agent selected but no SSH agent is running")
        exit(1)

    # Check if someone is actually authenticated
    if subprocess.run(['ssh-add', '-l']).returncode == 0:
        gitkeypair = pygit2.Keypair("git", None, None, "")
    else:
        logging.error("SSH agent selected but no active sessions")
        exit(1)

else:
    logging.info("No SSH agent selected but no password provided, trying passwordless authentication.")
    gitkeypair = pygit2.Keypair("git", os.path.expanduser("~/.ssh/id_rsa.pub"), os.path.expanduser("~/.ssh/id_rsa"), "")

gitcallbacks = pygit2.RemoteCallbacks(credentials=gitkeypair)

# Commit author
author = pygit2.Signature(args.commitname, args.commitemail)


def processversion(repo, application, versioninfo, suffix):
    logging.info("  -> {}{}".format(versioninfo['version'], suffix))

    branch = "refs/heads/{}{}".format(versioninfo['version'], suffix)
    remotebranch = "refs/remotes/origin/{}{}".format(versioninfo['version'], suffix)

    # Make sure we have a branch to work in
    if not repo.references.get(branch):
        remoteref = repo.references.get(remotebranch)
        if not remoteref:
            logging.info("     Creating branch")

            tree = repo.TreeBuilder().write()
            repo.create_commit(branch,
                               author,
                               author,
                               "New branch for {} {}{}".format(application['name'], versioninfo['version'], suffix),
                               tree,
                               []
                               )
        else:
            logging.info("     Using remote branch")
            repo.create_reference(branch, remoteref.resolve().target)

    logging.info("     Switching branch")
    repo.checkout(branch)

    # Clean the workdir
    for entry in os.listdir(repo.workdir):
        path = os.path.join(repo.workdir, entry)

        if os.path.isfile(path):
            os.unlink(path)
        else:
            if entry != '.git':
                shutil.rmtree(path)

    # Start processing templates
    templatedir = os.path.join(args.templatedir, application['template'])

    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(args.templatedir)
    )

    # Create the context from template and add version info
    context = application.get('context', {})
    context['version'] = versioninfo['version']
    context['url'] = versioninfo['zipUrl']

    logging.info("     Processing templates")
    # Walk the template directory
    for root, dirs, files in os.walk(templatedir):
        for template in files:
            outputfile, ext = os.path.splitext(template)

            # Only process files that have a .j2 extension
            if ext == '.j2':
                subpath = os.path.relpath(root, start=templatedir)
                outputpath = os.path.join(repo.workdir, subpath)

                # Make sure the directories exist
                os.makedirs(outputpath, exist_ok=True)

                # Process the template
                environment.get_template(os.path.join(application['template'], subpath, template)).stream(context).dump(os.path.join(outputpath, outputfile))

                # Make sure file permissions match
                mode = os.lstat(os.path.join(root, template)).st_mode
                os.chmod(os.path.join(outputpath, outputfile), mode)

    # If something changed, add files to the index and commit
    for path, flags in repo.status().items():
        if flags == pygit2.GIT_STATUS_CURRENT or flags == pygit2.GIT_STATUS_IGNORED:
            continue

        logging.info("     Comitting changes")

        repo.index.add_all()
        repo.index.write()
        tree = repo.index.write_tree()
        repo.create_commit(branch, author, author, "Update", tree, [repo.head.target])
        if not args.dontpush:
            logging.info("     Pushing branch")
            repo.remotes['origin'].push(['+' + branch], callbacks=gitcallbacks)
        else:
            logging.info("     Push disabled")

        break


def tagversion(repo, name, target):
    branch = "refs/heads/{}".format(name)
    remotebranch = "refs/remotes/origin/{}".format(name)
    targetbranch = "refs/heads/{}".format(target)

    branchref = repo.references.get(branch)
    remoteref = repo.references.get(remotebranch)
    targetref = repo.references.get(targetbranch)

    if branchref and \
            targetref and \
            remoteref and \
            branchref.resolve().target == targetref.resolve().target == remoteref.resolve().target:
        logging.info("{} already tagged as {}, skipping".format(target, name))
    else:
        logging.info("Tagging {} as {}".format(target, name))

        branchref = repo.create_reference(branch, targetref.resolve().target, force=True)

        # Only push if the remote reference is not the same as the local
        if remoteref == None or remoteref.resolve().target != branchref.resolve().target:
            if not args.dontpush:
                logging.info("Pushing branch")
                repo.remotes['origin'].push(['+' + branch], callbacks=gitcallbacks)
            else:
                logging.info("Push disabled")


def processconfiguration(repo, configuration):
    minimumversion = version.parse(configuration.get('minimumVersion', '0.0.1'))
    maximumversion = version.parse(configuration.get('maximumVersion', '999.999.999'))
    latestversion, latestmajor, latestminor = minimumversion, {}, {}
    suffix = configuration.get('suffix', '')

    for feed in configuration['feeds']:
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
                processversion(repo, configuration, versioninfo, suffix)

                # Hocus pocus to save latest major and minor versions
                if itemversion > latestversion:
                    latestversion = itemversion

                major = "{}".format(itemversion.release[0])
                if itemversion >= latestmajor.get(major, minimumversion):
                    latestmajor[major] = itemversion

                minor = "{}.{}".format(itemversion.release[0],  itemversion.release[1])
                if itemversion >= latestminor.get(minor, minimumversion):
                    latestminor[minor] = itemversion

    return (latestmajor, latestminor, latestversion)


def processapp(application):
    logging.info("Processing {}".format(application['name']))

    if 'repository' not in application:
        logging.warning("No repository configured, skipping")
        return

    # Extract directory name from repository
    m = re.match(r".*/([^/]*).git", application['repository'])
    path = os.path.join(args.workdir, m.group(1))

    if not os.path.exists(path):
        logging.info("Cloning to {}".format(path))

        # Clone the repository
        repo = pygit2.clone_repository(application['repository'], path, callbacks=gitcallbacks)

    repo = pygit2.Repository(path)

    versions = {}

    for configuration in application['configurations']:
        suffix = configuration.get('suffix', '')

        (latestmajor, latestminor, latestversion) = processconfiguration(repo, configuration)

        # Make sure that across configurations the major, minor and latest tags are respected
        if suffix not in versions:
            versions[suffix] = [latestmajor, latestminor, latestversion]

        else:
            for major, majorversion in latestmajor.items():
                if major not in versions[suffix][0] or majorversion > versions[suffix][0][major]:
                    versions[suffix][0][major] = majorversion

            for minor, minorversion in latestminor.items():
                if minor not in versions[suffix][1] or minorversion > versions[suffix][1][minor]:
                    versions[suffix][1][minor] = minorversion

            if latestversion > versions[suffix][2]:
                versions[suffix][2] = latestversion

    # Tag latest major and minor versions
    for suffix, (latestmajor, latestminor, latestversion) in versions.items():
        for major, majorversion in latestmajor.items():
            tagversion(repo, major + suffix, str(majorversion) + suffix)

        for minor, minorversion in latestminor.items():
            tagversion(repo, minor + suffix, str(minorversion) + suffix)

        tagversion(repo, "latest" + suffix, str(latestversion) + suffix)


if __name__ == '__main__':
    with open(args.repositories, 'r') as stream:
        repos = yaml.load(stream)

    with open(args.config, 'r') as stream:
        data = yaml.load(stream)

        for item in data:
            if item['name'] in repos:
                item['repository'] = repos[item['name']]

                if not args.templates or item['template'] in args.templates:
                    processapp(item)

            else:
                logging.info("No repository configured for {}".format(item['name']))

