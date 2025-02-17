FROM codx-junior:api AS api

FROM codx-junior:base

# API
ENV PYTHONPATH ${CODX_JUNIOR_PATH}/api

# VNC 
ENV DISPLAY :1
ENV DISPLAY_SHARED :2
ENV DISPLAY_WIDTH 1920
ENV DISPLAY_HEIGHT 1080
ENV VNC_NO_PASSWORD 1
# API virtual env
ENV CODX_JUNIOR_API_VENV /tmp/.venv_codx_junior_api
# Browser virtual env
ENV BROWSER_VENV /tmp/.venv_codx_junior_browser
# codx-junior API port
ENV CODX_JUNIOR_API_PORT 9984
# codx-junior WEB port
ENV WEB_PORT 9983
# codx-junior code-server port
ENV CODX_JUNIOR_CODER_PORT 9909
# codx-junior NOVNC port
ENV NOVNC_PORT 9986
# Filebrowser port
ENV CODX_JUNIOR_FILEBROWSER_PORT 9987
# Browser-use port
ENV BROWSER_PORT 9988

ENV CODX_JUNIOR_HOME /home/${USER}
USER ${USER}
WORKDIR ${CODX_JUNIOR_HOME}

RUN mkdir -p ${HOME}/projects

COPY --chown=${USER} api ${CODX_JUNIOR_PATH}/api
COPY --chown=${USER} client ${CODX_JUNIOR_PATH}/client
COPY --chown=${USER} browser ${CODX_JUNIOR_PATH}/browser
COPY --chown=${USER} scripts ${CODX_JUNIOR_PATH}/scripts
COPY --chown=${USER} supervisor.conf ${CODX_JUNIOR_PATH}

RUN chmod +x ${CODX_JUNIOR_PATH}/scripts/run_api.sh
RUN chmod +x ${CODX_JUNIOR_PATH}/scripts/run_client.sh

COPY --chown=${USER} code-server/User/settings.json ${HOME}/.local/share/code-server/User/settings.json

# Copy API venv
COPY --from=api --chown=${USER} $CODX_JUNIOR_API_VENV $CODX_JUNIOR_API_VENV

USER root
RUN mkdir -p ${CODX_SUPERVISOR_LOG_FOLDER}

CMD ["/entrypoint.sh"]