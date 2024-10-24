FROM debian:latest

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y curl wget novnc websockify supervisor nodejs npm \
        tigervnc-standalone-server locales python3 python3-venv \
        procps git sudo tesseract-ocr \
        firefox-esr && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Generate the required locale
# Set the locale
RUN sed -i '/en_US.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8

ENV VNC_NO_PASSWORD=1

# Install VNC and setup without password
RUN mkdir -p ~/.vnc && \
    echo "password" | vncpasswd -f > ~/.vnc/passwd && \
    chmod 600 ~/.vnc/passwd

# Install code-server latest version
RUN curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install supervisor
ENV SUPERVISOR_DIR=/etc/supervisord

# Create supervisord directory
RUN mkdir -p $SUPERVISOR_DIR

COPY supervisor.conf $SUPERVISOR_DIR

RUN mkdir -p /projects

COPY . /projects/codx-junior
RUN rm -rf /projects/codx-junior/api/.venv
RUN chmod +x /projects/codx-junior/run_api.sh
RUN chmod +x /projects/codx-junior/run_client.sh

ENV PYTHONPATH=/projects/codx-junior/api

RUN git config --global --add safe.directory '*'

COPY firefox/start-firefox.sh /start-firefox.sh

ENV DISPLAY=:1
ENV DISPLAY_WIDTH=1920
ENV DISPLAY_HEIGHT=1080

# codx-junior API port
ENV API_PORT=9984
# codx-junior WEB port
ENV WEB_PORT=9983
# codx-junior code-server port
ENV CODER_PORT=9909
# codx-junior NOVNC port
ENV NOVNC_PORT=9986

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord/supervisor.conf"]