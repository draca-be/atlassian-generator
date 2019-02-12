# Atlassian Generator

This tool generates Dockerfiles in git repositories automatically tagging them 
for usage with Docker hub.

It does this by fetching the available versions from the Atlassian website so 
you can run it in a cron to have on-the-fly creation of new images as soon as
a new version is available for download.

You can find the generated images in [the Docker hub](https://hub.docker.com/u/draca/).

## Dependencies

* libgit2-devel

## Usage

It's probably best if you run this in a virtualenv

```bash
# pip install -r requirements.txt
# python generator.py --help 
```

## Templates

Each entry in the config file should point to a directory in the templates folder.
All files ending in .j2 are parsed by Jinja2 and output in the repository in the 
same location (minus the .j2 extension). All files with other extensions are ignored.
Subdirectories are traversed and recreated in the output repository. Symlinks are not
followed.

Note that Jinja2 allows you to include files. If you want to reuse certain files you 
probably don't want to give those a .j2 extension.

Following variables are available in the template:
* version
* url

## Repositories

* master matches the latest version
* the script force pushes all the branches
* all branches are created as orphan branches

## Thanks

While originally created for own usage this tool is now also used by [iDalko](https://www.idalko.com) who
allow me time to work on it. This combined with leveraging their knowledge results in a higher quality of 
Dockerfiles and images.

## Disclaimer

Use this script at your own risk. If this destroys existing repositories, docker
images, your home or your relationship we can take no responsibility.

There is no affiliation between the creator of this script and Atlassian.
