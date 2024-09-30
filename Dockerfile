FROM debian:latest

# Install novnc, VNC server, locales, and any necessary dependencies
RUN apt-get update && \
    apt-get install -y curl wget novnc websockify supervisor tigervnc-standalone-server locales python3 python3-venv procps nodejs git npm sudo && \
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
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Install supervisor
ENV SUPERVISOR_DIR=/etc/supervisord

# Create supervisord directory
RUN mkdir -p $SUPERVISOR_DIR

ENV API_PORT=9451
ENV WEB_PORT=9452
ENV API_URL="http://0.0.0.0:${API_PORT}"

COPY supervisor.conf $SUPERVISOR_DIR


RUN mkdir -p /projects

COPY . /projects/codx-junior
RUN chmod +x /projects/codx-junior/run_api.sh
RUN chmod +x /projects/codx-junior/run_client.sh

RUN cd /projects/codx-junior && \
    bash ./install.sh

ENV PYTHONPATH=/usr/local/codx-cli/codx-junior/api

EXPOSE 6080
EXPOSE 9080
EXPOSE $API_PORT
EXPOSE $WEB_PORT

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord/supervisor.conf"]