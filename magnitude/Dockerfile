#####################################################################################
# Magnitude test image
#
# Goal: build an image that can run the open-source Magnitude inference engine
#       (https://github.com/magnitudedev/magnitude) head-less inside a container
#       and download / serve a small model that fits the current hardware.
#
# Notes:
#   * Magnitude requires glibc >= 2.34  ->  debian:12 (glibc 2.36) is fine.
#   * Alpine / musl packages do NOT exist.  Do not switch the base image.
#   * The Linux package ships the `magnitude` CLI; `magnitude serve` runs
#     without a graphical session, which is exactly what a container needs.
#####################################################################################
FROM debian:12-slim

# CPU architecture of the machine running the build:
#   x86_64  -> x64     (default)
#   aarch64 -> arm64
ARG MAGNITUDE_ARCH=x64

ENV DEBIAN_FRONTEND=noninteractive \
    MAGNITUDE_USER=magnitude \
    MAGNITUDE_HOME=/home/magnitude \
    MAGNITUDE_TOOLS=/opt/magnitude-tools \
    MAGNITUDE_PORT=10100 \
    HOME=/home/magnitude \
    PATH=/home/magnitude/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# --- base tooling --------------------------------------------------------------
#   curl  : download the installer and probe the API
#   jq    : build/parse JSON payloads in the test scripts
#   mawk  : small awk for the tokens/s calculation
#   tini  : correct PID-1 signal handling for `magnitude serve`
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      jq \
      mawk \
      tini \
 && rm -rf /var/lib/apt/lists/*

# --- install Magnitude (Linux .deb) --------------------------------------------
# `apt install ./pkg.deb` also resolves the desktop libraries Magnitude needs.
RUN curl -fL -o /tmp/magnitude-desktop.deb \
      "https://magnitude.dev/api/installer?os=linux&arch=${MAGNITUDE_ARCH}&package=deb" \
 && apt-get update \
 && apt-get install -y /tmp/magnitude-desktop.deb \
 && apt-get -y --fix-broken install \
 && rm -f /tmp/magnitude-desktop.deb \
 && rm -rf /var/lib/apt/lists/* \
 && (command -v magnitude >/dev/null 2>&1 \
       && echo "magnitude CLI installed at: $(command -v magnitude)" \
       || echo "WARNING: 'magnitude' not on PATH after install; the entrypoint will look in common locations")

# --- non-root user -------------------------------------------------------------
# Downloads/settings live in $MAGNITUDE_HOME/.magnitude and are persisted
# through a compose volume.
RUN useradd --create-home --uid 1000 --shell /bin/bash ${MAGNITUDE_USER} \
 && mkdir -p ${MAGNITUDE_HOME}/.magnitude ${MAGNITUDE_HOME}/.local/bin \
 && chown -R ${MAGNITUDE_USER}:${MAGNITUDE_USER} ${MAGNITUDE_HOME}

# --- helper scripts (entrypoint + model test harness) --------------------------
COPY scripts/ ${MAGNITUDE_TOOLS}/
RUN chmod +x ${MAGNITUDE_TOOLS}/*.sh

USER ${MAGNITUDE_USER}
WORKDIR ${MAGNITUDE_HOME}

# Magnitude server / OpenAI-compatible API
EXPOSE 10100

HEALTHCHECK --interval=15s --timeout=5s --start-period=45s --retries=20 \
  CMD curl -fsS http://127.0.0.1:10100/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/opt/magnitude-tools/entrypoint.sh"]
CMD ["serve"]
