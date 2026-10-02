#!/usr/bin/env bash
set -Eeuo pipefail

# ─── Constants ───────────────────────────────────────────────────────────────

SCRIPT_VERSION="2.0.0"
MODE="${1:---dry-run}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="/var/log/vulnerable-apps-remediation-${TIMESTAMP}.log"
SUMMARY_ERRORS=()
SUMMARY_UPGRADED=()
SUMMARY_SKIPPED=()

# ─── Colors ──────────────────────────────────────────────────────────────────

if [[ -t 1 ]]; then
  C_RESET='\033[0m'
  C_BOLD='\033[1m'
  C_RED='\033[0;31m'
  C_YELLOW='\033[0;33m'
  C_GREEN='\033[0;32m'
  C_CYAN='\033[0;36m'
  C_DIM='\033[2m'
else
  C_RESET='' C_BOLD='' C_RED='' C_YELLOW='' C_GREEN='' C_CYAN='' C_DIM=''
fi

# ─── Logging ─────────────────────────────────────────────────────────────────

log()      { echo -e "${C_DIM}[$(date +%H:%M:%S)]${C_RESET} $*"; }
log_info() { echo -e "${C_CYAN}${C_BOLD}[INFO]${C_RESET}  $*"; }
log_ok()   { echo -e "${C_GREEN}${C_BOLD}[OK]${C_RESET}    $*"; }
log_warn() { echo -e "${C_YELLOW}${C_BOLD}[WARN]${C_RESET}  $*"; }
log_err()  { echo -e "${C_RED}${C_BOLD}[ERROR]${C_RESET} $*" >&2; }
log_dry()  { echo -e "${C_DIM}[DRY-RUN]${C_RESET} $(printf ' %q' "$@")"; }

section() {
  echo
  echo -e "${C_BOLD}${C_CYAN}══════════════════════════════════════════${C_RESET}"
  echo -e "${C_BOLD}${C_CYAN}  $*${C_RESET}"
  echo -e "${C_BOLD}${C_CYAN}══════════════════════════════════════════${C_RESET}"
}

# ─── Argument Validation ─────────────────────────────────────────────────────

if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
  log_err "Usage: $0 [--dry-run|--apply]"
  exit 1
fi

if ! command -v apt-get >/dev/null 2>&1; then
  log_err "This script requires apt-get (Debian/Ubuntu)."
  exit 1
fi

if [[ "$MODE" == "--apply" && "${EUID}" -ne 0 ]]; then
  log_err "Run this script as root: sudo $0 --apply"
  exit 1
fi

# ─── Logging Setup ───────────────────────────────────────────────────────────

if [[ "$MODE" == "--apply" ]]; then
  exec > >(tee -a "$LOG_FILE") 2>&1
  log_info "Log saved to: $LOG_FILE"
fi

# ─── Helpers ─────────────────────────────────────────────────────────────────

# Execute or print depending on mode. Returns exit code of command (best-effort).
run() {
  if [[ "$MODE" == "--dry-run" ]]; then
    log_dry "$@"
    return 0
  fi

  local cmd_str
  cmd_str="$(printf '%q ' "$@")"

  if "$@"; then
    return 0
  else
    local exit_code=$?
    log_err "Command failed (exit $exit_code): $cmd_str"
    SUMMARY_ERRORS+=("exit=$exit_code :: $cmd_str")
    return 0  # best-effort: never abort on individual command failure
  fi
}

is_installed() {
  dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

package_exists() {
  apt-cache show "$1" >/dev/null 2>&1
}

dedupe_packages() {
  awk '!seen[$0]++'
}

upgrade_package() {
  local pkg="$1"
  if ! is_installed "$pkg"; then
    SUMMARY_SKIPPED+=("$pkg (not installed)")
    return 0
  fi

  local installed candidate
  installed="$(dpkg-query -W -f='${Version}' "$pkg" 2>/dev/null || echo 'unknown')"
  candidate="$(apt-cache policy "$pkg" 2>/dev/null | awk '/Candidate:/ {print $2}' || echo 'unknown')"

  if [[ "$installed" == "$candidate" ]]; then
    SUMMARY_SKIPPED+=("$pkg ($installed) — already at latest version")
    log "${C_DIM}$pkg is already at the latest version ($installed)${C_RESET}"
    return 0
  fi

  log_info "Upgrading $pkg: $installed → $candidate"
  run apt-get "${APT_OPTS[@]}" install --only-upgrade "$pkg"
  SUMMARY_UPGRADED+=("$pkg: $installed → $candidate")
}

graceful_nginx() {
  local action="$1"  # reload | stop | start
  if systemctl is-active --quiet nginx 2>/dev/null; then
    case "$action" in
      reload)
        log_info "Reloading nginx (zero downtime)..."
        run nginx -t && run systemctl reload nginx || log_warn "nginx reload failed, continuing..."
        ;;
      stop)
        log_warn "Stopping nginx temporarily..."
        run systemctl stop nginx || true
        ;;
      start)
        log_info "Starting nginx..."
        run systemctl start nginx || log_warn "Could not start nginx."
        ;;
    esac
  fi
}

# ─── Configuration ───────────────────────────────────────────────────────────

APT_OPTS=(
  -y
  -o Dpkg::Options::=--force-confdef
  -o Dpkg::Options::=--force-confold
  -o APT::Get::Show-Upgraded=true
)

# Packages confirmed present/relevant for Debian 13 trixie.
# Sun JRE 1.5 section removed: OpenJDK 21 (Temurin) is already installed.
# Xwayland/xserver packages kept as declared in original target list.
TARGET_PACKAGES=(
  # Web / network
  nginx
  curl
  wget
  openssl
  # Shell / core utils
  bash-completion
  coreutils
  util-linux
  tar
  xz-utils
  unzip
  nano
  patch
  # System
  apt
  sudo
  systemd
  iptables
  libcap2
  libtasn1-6
  libgcrypt20
  # Scripting / dev tools
  perl
  python3.13
  git
  jq
  gdb
  binutils
  ppp
  # X11 (kept from original — harmless if not installed)
  xwayland
  xdg-utils
  x11-xkb-utils
  xserver-xorg-video-nouveau
  xserver-xorg-core
  xserver-common
  xterm
  # Runtime
  default-jre-headless
)

# ─── Banner ──────────────────────────────────────────────────────────────────

section "fix_vulnerable_apps.sh v${SCRIPT_VERSION}"
log_info "Mode   : ${C_BOLD}$MODE${C_RESET}"
log_info "Host   : $(hostname)"
log_info "OS     : $(grep PRETTY_NAME /etc/os-release | cut -d= -f2- | tr -d '\"')"
log_info "Kernel : $(uname -r)"
log_info "Arch   : $(dpkg --print-architecture)"
echo

# ─── Held Packages ───────────────────────────────────────────────────────────

section "Held packages"
HELD_PACKAGES="$(apt-mark showhold 2>/dev/null || true)"
if [[ -n "$HELD_PACKAGES" ]]; then
  log_warn "Held packages (may block upgrades):"
  echo "$HELD_PACKAGES" | while IFS= read -r h; do
    log_warn "  hold: $h"
  done
else
  log_ok "No held packages found."
fi

# ─── APT Update ──────────────────────────────────────────────────────────────

section "Updating APT indexes"
run apt-get update

# ─── Upgrade Target Packages ─────────────────────────────────────────────────

section "Upgrading vulnerable target packages"

for pkg in "${TARGET_PACKAGES[@]}"; do
  upgrade_package "$pkg"
done

# ─── Linux Kernel Packages ───────────────────────────────────────────────────

section "Upgrading installed kernel packages"

KERNEL_PKGS=()
while IFS= read -r pkg; do
  [[ -n "$pkg" ]] && KERNEL_PKGS+=("$pkg")
done < <(
  dpkg-query -W -f='${Package}\n' \
    'linux-image*' 'linux-headers*' 'linux-libc-dev' 'linux-kbuild*' \
    2>/dev/null | dedupe_packages || true
)

if [[ "${#KERNEL_PKGS[@]}" -gt 0 ]]; then
  for pkg in "${KERNEL_PKGS[@]}"; do
    upgrade_package "$pkg"
  done
else
  log_info "No installed kernel packages found (expected in a Docker container)."
fi

# Kernel meta-package (best-effort, non-fatal in containers)
ARCH="$(dpkg --print-architecture)"
KERNEL_META=""
case "$ARCH" in
  amd64)
    if uname -r | grep -q 'cloud'; then
      KERNEL_META="linux-image-cloud-amd64"
    elif uname -r | grep -q 'rt'; then
      KERNEL_META="linux-image-rt-amd64"
    else
      KERNEL_META="linux-image-amd64"
    fi
    ;;
  arm64)
    KERNEL_META="linux-image-arm64"
    ;;
esac

if [[ -n "$KERNEL_META" ]] && package_exists "$KERNEL_META"; then
  log_info "Ensuring kernel meta-package: $KERNEL_META"
  run apt-get "${APT_OPTS[@]}" install "$KERNEL_META"
else
  log_info "Kernel meta-package not applicable in this container ($ARCH) — skipped."
fi

# ─── Nginx Graceful Reload ────────────────────────────────────────────────────

section "Reloading nginx"
graceful_nginx reload

# ─── Full Upgrade ─────────────────────────────────────────────────────────────

section "Full-upgrade (dependencies and pending patches)"
log_warn "full-upgrade may remove packages to resolve dependencies."
log_warn "Review the output carefully."
run apt-get "${APT_OPTS[@]}" full-upgrade

# ─── Autoremove ───────────────────────────────────────────────────────────────

section "Removing obsolete packages"
run apt-get "${APT_OPTS[@]}" autoremove --purge

# ─── Clean ────────────────────────────────────────────────────────────────────

section "Cleaning APT cache"
run apt-get clean

# ─── Version Summary ──────────────────────────────────────────────────────────

section "Version summary"
printf "%-40s %-30s %-30s\n" "PACKAGE" "INSTALLED" "CANDIDATE"
printf "%-40s %-30s %-30s\n" "$(printf '─%.0s' {1..40})" "$(printf '─%.0s' {1..30})" "$(printf '─%.0s' {1..30})"

for pkg in "${TARGET_PACKAGES[@]}" "$KERNEL_META" default-jre-headless; do
  [[ -z "$pkg" ]] && continue
  if is_installed "$pkg"; then
    iv="$(dpkg-query -W -f='${Version}' "$pkg" 2>/dev/null || echo '?')"
    cv="$(apt-cache policy "$pkg" 2>/dev/null | awk '/Candidate:/ {print $2}' || echo '?')"
    if [[ "$iv" == "$cv" ]]; then
      printf "${C_GREEN}%-40s %-30s %-30s${C_RESET}\n" "$pkg" "$iv" "$cv"
    else
      printf "${C_YELLOW}%-40s %-30s %-30s${C_RESET}\n" "$pkg" "$iv" "→ $cv"
    fi
  fi
done

# ─── Final Report ─────────────────────────────────────────────────────────────

section "Final report"

if [[ "${#SUMMARY_UPGRADED[@]}" -gt 0 ]]; then
  log_ok "Upgraded packages (${#SUMMARY_UPGRADED[@]}):"
  for item in "${SUMMARY_UPGRADED[@]}"; do
    echo -e "  ${C_GREEN}✔${C_RESET} $item"
  done
fi

if [[ "${#SUMMARY_SKIPPED[@]}" -gt 0 ]]; then
  log_info "Skipped packages (${#SUMMARY_SKIPPED[@]}):"
  for item in "${SUMMARY_SKIPPED[@]}"; do
    echo -e "  ${C_DIM}– $item${C_RESET}"
  done
fi

if [[ "${#SUMMARY_ERRORS[@]}" -gt 0 ]]; then
  echo
  log_err "Errors encountered (${#SUMMARY_ERRORS[@]}) — review the log:"
  for item in "${SUMMARY_ERRORS[@]}"; do
    echo -e "  ${C_RED}✘${C_RESET} $item"
  done
  echo
  log_warn "The script continued in best-effort mode. Please review the errors above."
else
  echo
  log_ok "No errors detected."
fi

if [[ "$MODE" == "--apply" ]]; then
  echo
  if [[ -f /var/run/reboot-required ]]; then
    log_warn "REBOOT REQUIRED:"
    cat /var/run/reboot-required.pkgs 2>/dev/null || true
  else
    log_ok "No reboot required (expected in a Docker container)."
  fi

  log_info "Full log available at: $LOG_FILE"
else
  echo
  log_info "Dry-run complete. ${C_BOLD}No changes were applied.${C_RESET}"
  log_info "To apply changes run: ${C_BOLD}sudo $0 --apply${C_RESET}"
fi

echo
log_ok "Done."