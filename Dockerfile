FROM lscr.io/linuxserver/webtop:debian-kde

COPY . /config/codx-junior
RUN cd /config/codx-junior && bash codx-junior install