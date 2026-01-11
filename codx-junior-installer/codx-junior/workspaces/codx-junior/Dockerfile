FROM ghcr.io/linuxserver/webtop:debian-kde

RUN curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s

RUN codx code-server

EXPOSE 9080