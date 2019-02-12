#!/bin/bash

SERVERXML="${CONF_INSTALL}/conf/server.xml"
SETENV="${CONF_INSTALL}/bin/setenv.sh"

if [ -f ${SERVERXML}.orig ]; then
    # Copy back the original server.xml for clean editing
    cp ${SERVERXML}.orig ${SERVERXML}
else
    # Make a backup of server.xml
    cp ${SERVERXML} ${SERVERXML}.orig
fi

if [ -f ${SETENV}.orig ]; then
    # Copy back the original setenv.sh for clean editing
    cp ${SETENV}.orig ${SETENV}
else
    # Make a backup of setenv.sh
    cp ${SETENV} ${SETENV}.orig
fi

# Set the timezone if needed
TZ_FILE="/usr/share/zoneinfo/${CONTAINER_TZ}"

if [ -n "${CONTAINER_TZ}" ] && [ -f ${TZ_FILE} ]; then
    cp /${TZ_FILE} /etc/localtime
    echo "${CONTAINER_TZ}" > /etc/timezone
fi

# Import certificates if any available
find ${CONF_CERTS} -name *.crt -print0 | while IFS= read -r -d $'\0' line; do
    name=$(basename $line)

    # Make sure if one exists it is deleted first
    ${JAVA_HOME}/bin/keytool -delete -storepass changeit -noprompt -alias "${name}" -keystore ${JAVA_HOME}/jre/lib/security/cacerts 2>&1 >/dev/null
    ${JAVA_HOME}/bin/keytool -import -storepass changeit -noprompt -alias "${name}" -keystore ${JAVA_HOME}/jre/lib/security/cacerts -file "${line}"
done


if [ -n "${CONF_PROXY_NAME}" ]; then
    sed -i "s/port=\"8090\"/port=\"8090\" proxyName=\"${CONF_PROXY_NAME}\"/g" ${SERVERXML}
fi
if [ -n "${CONF_PROXY_PORT}" ]; then
    sed -i "s/port=\"8090\"/port=\"8090\" proxyPort=\"${CONF_PROXY_PORT}\"/g" ${SERVERXML}
fi
if [ -n "${CONF_PROXY_SCHEME}" ]; then
    sed -i "s/port=\"8090\"/port=\"8090\" scheme=\"${CONF_PROXY_SCHEME}\"/g" ${SERVERXML}
fi
if [ -n "${CONF_CONTEXT_PATH}" ]; then
    sed -i "s:path=\"\":path=\"${CONF_CONTEXT_PATH}\":g" ${SERVERXML}
fi

if [ -n "${DISABLE_NOTIFICATIONS}" ]; then
    CONF_ARGS="-Datlassian.mail.senddisabled=true -Datlassian.mail.fetchdisabled=true -Datlassian.mail.popdisabled=true ${CONF_ARGS}"
fi

sed -i "s#-Xms[0-9]\+[kmg] -Xmx[0-9]\+[kmg]#-Xms${JVM_MINIMUM_MEMORY} -Xmx${JVM_MAXIMUM_MEMORY} ${CONF_ARGS}#g" ${SETENV}

if [ "x${RUN_USER}" != "x$(stat -c %U ${CONF_HOME})" ]; then
    chown -R ${RUN_USER}:${RUN_GROUP} "${CONF_HOME}"
fi

if [ "x${RUN_USER}" != "x$(stat -c %U ${CONF_INSTALL})" ]; then
    chown -R ${RUN_USER}:${RUN_GROUP} "${CONF_INSTALL}"
fi

sed -i "s/CONF_USER=\"[^\"]*\"/CONF_USER=\"${RUN_USER}\"/g" "${CONF_INSTALL}/bin/user.sh"

exec "$@"
