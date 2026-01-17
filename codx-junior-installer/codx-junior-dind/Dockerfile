# Use the official Docker-in-Docker image as base
FROM docker:27-dind

# Install bash if your scripts need it
RUN apk add --no-cache bash

# Copy custom entrypoint wrapper
COPY ./codx-junior-installer/codx-junior-dind/entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/entrypoint-wrapper.sh

# Create the custom initialization directory similar to LS.io
RUN mkdir -p /custom-cont-init.d
COPY ./codx-junior-installer/codx-junior-dind/codx-junior-dind-init.sh /custom-cont-init.d/codx-junior-dind-init.sh

 # mmmm rethink this
 # COPY . /codx-junior

EXPOSE 80
EXPOSE 443

# Use the wrapper as the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]
