################################################################################
# codx-junior default workspace desktop
#
# Base: kasmweb/ubuntu-noble-desktop — Ubuntu 24.04 desktop streamed by KasmVNC
#       on https://<container>:6901 (user: kasm_user, password: $VNC_PW)
# Adds: VSCodium (https://vscodium.com) from the official apt repository, wired
#       into kasm_user's desktop and started with the session.
#
# The same image also runs VSCodium's browser server (`codium serve-web`) for
# the "coder" route — see docker-compose.yaml `codx-junior-coder` service.
#
# Build:
#   docker compose build codx-junior-default
################################################################################
ARG KASM_DESKTOP_IMAGE=kasmweb/ubuntu-noble-desktop:1.18.0
FROM ${KASM_DESKTOP_IMAGE}

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

################################################################################
# VSCodium — official apt repository
# https://vscodium.com/#install-on-debian-ubuntu-debian-derivatives
################################################################################
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://gitlab.com/paulcarroty/vscodium-deb-rpm-repo/raw/master/pub.gpg \
        | gpg --dearmor -o /usr/share/keyrings/vscodium-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/vscodium-archive-keyring.gpg] https://download.vscodium.com/debs vscodium main" \
        > /etc/apt/sources.list.d/vscodium.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends codium \
    && rm -rf /var/lib/apt/lists/*

################################################################################
# Desktop integration for kasm-user (uid 1000)
#
# --no-sandbox: Electron/Chromium user namespaces are not available in the
# container, the flag is required for VSCodium to start.
################################################################################
RUN printf '%s\n' \
      '[Desktop Entry]' \
      'Type=Application' \
      'Name=VSCodium' \
      'GenericName=Text Editor' \
      'Comment=Code editing. Redefined. (VSCodium)' \
      'Exec=/usr/bin/codium --no-sandbox %F' \
      'Icon=vscodium' \
      'Terminal=false' \
      'Categories=Development;IDE;TextEditor;' \
      'StartupNotify=false' \
      'StartupWMClass=VSCodium' \
      > /usr/share/applications/vscodium.desktop \
    && mkdir -p /home/kasm-user/Desktop \
                /home/kasm-user/.config/autostart \
                /home/kasm-user/.config/VSCodium \
                /home/kasm-user/.vscode-oss/extensions \
                /home/kasm-user/.vscode-server \
    && cp /usr/share/applications/vscodium.desktop /home/kasm-user/Desktop/vscodium.desktop \
    && chmod +x /home/kasm-user/Desktop/vscodium.desktop \
    && cp /usr/share/applications/vscodium.desktop /home/kasm-user/.config/autostart/vscodium.desktop \
    && chown -R 1000:0 /home/kasm-user

################################################################################
# KasmVNC Pre-authentication & Bypassing
#
# 1. Create passive credential files required for hook validation
# 2. Tell KasmVNC to look for its static files natively at root /
################################################################################
RUN echo -e "irrelevant_password_bypass\nirrelevant_password_bypass\n" | kasmvncpasswd -u kasm-user /home/kasm-user/.kasmpasswd \
    && chown 1000:0 /home/kasm-user/.kasmpasswd \
    && sed -i 's|# public_path:.*|public_path: /|g' /etc/kasmvnc/kasmvnc.yaml \
    && sed -i 's/crossorigin src/crossorigin="use-credentials" src/g' /usr/share/kasmvnc/www/vnc.html

# KasmVNC web endpoint (https)
EXPOSE 6901
# VSCodium browser server (`codium serve-web`)
EXPOSE 9080

################################################################################
# Restore the base image's default runtime user.
#
# kasmweb/ubuntu-noble-desktop ends with `USER 1000` / `HOME=/home/kasm-user`.
# Leaving USER root here would run the desktop session as root, so VSCodium
# config, extensions, the desktop shortcut and XDG autostart would resolve to
# /root instead of the mounted /home/kasm-user paths.
################################################################################
USER 1000
