# Base
FROM debian:12 AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV CODX_JUNIOR_API_VENV=/tmp/.venv_codx_junior_api

RUN apt update && apt install -y sudo locales git fuse3 fuse-overlayfs

RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "LANG=en_US.UTF-8" > /etc/locale.conf
RUN locale-gen en_US.UTF-8

ARG USER_UID=1001
ARG USER_GID=1001
ENV USER="codx-junior"
ENV HOME="/home/${USER}"

# Create user with specified UID and GID
RUN groupadd -g ${USER_GID} codx-junior
RUN useradd -u ${USER_UID} -g ${USER_GID} -s /bin/bash -m -d ${HOME} $USER

# Add user to sudoers with no password
RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USER}
WORKDIR ${HOME}/codx-junior

COPY --chown=${USER} client ./client
COPY --chown=${USER} api ./api
COPY --chown=${USER} scripts ./scripts
COPY --chown=${USER} codx-junior ./codx-junior
COPY --chown=${USER} set_env.sh .
COPY --chown=${USER} entrypoint.sh .

ENV CODX_JUNIOR_PATH=${HOME}/codx-junior

RUN bash scripts/install_base.sh
RUN bash scripts/install_noVNC.sh

## Install API
FROM base AS api

USER ${USER}
WORKDIR ${HOME}/codx-junior

ENV CODX_JUNIOR_APPS="api"
RUN bash scripts/install.sh

## codx-junior
FROM base

USER ${USER}
WORKDIR ${HOME}/codx-junior

COPY --chown=${USER} --from=api $CODX_JUNIOR_API_VENV $CODX_JUNIOR_API_VENV

COPY --chown=${USER} entrypoint.sh /entrypoint.sh
RUN chmod +x /home/codx-junior/codx-junior/entrypoint.sh

ENV CODX_JUNIOR_APPS="client llm-factory docker"
RUN /home/codx-junior/codx-junior/entrypoint.sh install

# Set up Docker volume  
VOLUME /var/lib/docker  

CMD [ "/home/codx-junior/codx-junior/entrypoint.sh" ]