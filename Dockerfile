FROM debian:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y sudo locales git

RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "LANG=en_US.UTF-8" > /etc/locale.conf
RUN locale-gen en_US.UTF-8

ARG USER_UID=1000
ARG USER_GID=1000
ENV USER="codx-junior"
ENV HOME="/home/${USER}"

ENV DEBUG=""

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
COPY --chown=${USER} lxde ./lxde
COPY --chown=${USER} set_env.sh .

COPY --chown=${USER} supervisor.conf ./supervisor.conf

COPY --chown=${USER} entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN /entrypoint.sh install

CMD [ "/entrypoint.sh" ]