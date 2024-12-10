FROM debian:latest AS API

ENV CODX_JUNIOR_HOME=/projects/codx-junior
# API virtual env
ENV API_VENV=/tmp/.venv_codx_junior_api

RUN apt-get update && \
    apt-get install -y python3 python3-venv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY api /projects/codx-junior/api
COPY scripts /projects/codx-junior/scripts

RUN chmod +x /projects/codx-junior/scripts/install_api.sh
RUN bash /projects/codx-junior/scripts/install_api.sh


FROM debian:latest

# User
ARG USER_ID=1000
ARG USER_GROUP=1000
ENV USER=codxuser
ENV HOME=/home/${USER}

ENV DEBIAN_FRONTEND=noninteractive

# API
ENV CODX_JUNIOR_HOME=${HOME}/projects/codx-junior
ENV PYTHONPATH=${CODX_JUNIOR_HOME}/api

# VNC 
ENV DISPLAY=:1
ENV DISPLAY_WIDTH=1920
ENV DISPLAY_HEIGHT=1080
ENV VNC_NO_PASSWORD=1

# Locales
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

# API virtual env
ENV API_VENV=/tmp/.venv_codx_junior_api
# Browser virtual env
ENV BROWSER_VENV=/tmp/.venv_codx_junior_browser
# codx-junior API port
ENV API_PORT=9984
# codx-junior WEB port
ENV WEB_PORT=9983
# codx-junior code-server port
ENV CODER_PORT=9909
# codx-junior NOVNC port
ENV NOVNC_PORT=9986
# Filebrowser port
ENV FILEBROWSER_PORT=9987
# Browser-use port
ENV BROWSER_PORT=9988
# Serving client from API
ENV STATIC_FOLDER=${CODX_JUNIOR_HOME}/client/dist

# Install packages
RUN apt-get update && \
    apt-get install -y curl wget novnc websockify supervisor nodejs npm \
        tigervnc-standalone-server locales python3 python3-venv \
        procps git sudo tesseract-ocr lxde-core && \
    apt-get remove -y xscreensaver && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Generate the required locale
# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen

# Install supervisor
# Create supervisord directory
RUN mkdir -p /etc/supervisord
COPY supervisor.conf /etc/supervisord/codx-junior.conf

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install VNC and setup without password
RUN mkdir -p /root/.vnc && \
    echo "password" | vncpasswd -f > /root/.vnc/passwd && \
    chmod 600 /root/.vnc/passwd

RUN touch /root/.Xauthority

# VNC
COPY xstartup /root/.vnc/xstartup

# Create USER
RUN groupadd -g ${USER_GROUP} ${USER} && \
    useradd -m -u ${USER_ID} -g ${USER_GROUP} -s /bin/bash ${USER} && \
    echo "${USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USER}
WORKDIR ${CODX_JUNIOR_HOME}

RUN mkdir -p ${HOME}/projects

COPY --chown=${USER} api ${CODX_JUNIOR_HOME}/api
COPY --chown=${USER} client ${CODX_JUNIOR_HOME}/client
COPY --chown=${USER} browser ${CODX_JUNIOR_HOME}/browser
COPY --chown=${USER} scripts ${CODX_JUNIOR_HOME}/scripts

RUN chmod +x ${CODX_JUNIOR_HOME}/scripts/run_api.sh
RUN chmod +x ${CODX_JUNIOR_HOME}/scripts/run_client.sh


RUN git config --global --add safe.directory '*'

# codx APPS
RUN curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s
RUN codx chrome
RUN codx docker
RUN codx filebrowser
RUN codx coder

COPY --chown=${USER} code-server/User/settings.json ${HOME}/.local/share/code-server/User/settings.json

# Copy API venv
COPY --from=API --chown=${USER} $API_VENV $API_VENV

USER root
CMD ["/entrypoint.sh"]