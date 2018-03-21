# Atlassian Generator

This tool generates Dockerfiles in git repositories automatically tagging them 
for usage with Docker hub.

It does this by fetching the available versions from the Atlassian website so 
you can run it in a cron to have on-the-fly creation of new images as soon as
a new version is available for download.

## Repositories

* master matches the latest version
* the script force pushes all the tags, effectively overwriting existing tags

## Disclaimer

Use this script at your own risk. If this destroys existing repositories, docker
images, your home or your relationship we can take no responsibility.

There is no affiliation between the creator of this script and Atlassian.