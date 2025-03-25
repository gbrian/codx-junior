FROM debian:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt install -y sudo locales git

RUN echo "LC_ALL=en_US.UTF-8" >> /etc/environment
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "LANG=en_US.UTF-8" > /etc/locale.conf
RUN locale-gen en_US.UTF-8

ARG CODX_JUNIOR_BRANCH=v1.0-hello-codx-junior 
ENV CODX_JUNIOR_BRANCH=$CODX_JUNIOR_BRANCH
# Check if USER_UID and USER_GID are set; otherwise, use default value 1000
ARG USER_UID=1000
ARG USER_GID=1000
ENV USER="codx-junior"
ENV HOME="/home/${USER}"

# Create user with specified UID and GID
RUN groupadd -g ${USER_GID} codx-junior
RUN useradd -u ${USER_UID} -g ${USER_GID} -s /bin/bash -m -d ${HOME} $USER

# Add user to sudoers with no password
RUN echo "$USER ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER ${USER}

COPY --chown=${USER} entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]