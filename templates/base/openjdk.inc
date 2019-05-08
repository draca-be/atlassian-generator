FROM adoptopenjdk/openjdk8:jdk8u212-b03-alpine

{#  This includes some basic stuff that is not present in the image but which we really like / need:

* Bash
* Fonts

#}
RUN echo @edge http://dl-cdn.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories \
    && echo @edge http://dl-cdn.alpinelinux.org/alpine/edge/main >> /etc/apk/repositories \
    && apk add --no-cache \
    bash \
    ttf-dejavu fontconfig && \
    fc-cache -f

{# This is necessary for some functionalities:

* Usage of fontconfig by Jira / Confluence
* Get a working Chromium installation if you need EazyBI

This (hopefully) should become obsolete in the future, check this bug:

https://github.com/AdoptOpenJDK/openjdk-docker/issues/75

#}
ENV LD_LIBRARY_PATH=/usr/lib:/lib
RUN ln -s /usr/lib/libfontconfig.so.1 /usr/lib/libfontconfig.so