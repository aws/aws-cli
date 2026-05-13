#!/usr/bin/env bash
#
# AWS CLI v2 install script for Linux and macOS.
#
# Defaults to a user-local install under XDG paths. Use --system for the
# traditional /usr/local layout (requires root). See --help for details.
#
# This is the customer-facing entry point downloaded over curl|bash. It is
# distinct from scripts/install (the Python installer bundled inside the
# Linux .zip artifact); this script downloads and invokes that bundled
# installer.

set -euo pipefail

readonly SCRIPT_VERSION="0.0.0-dev"
readonly DOWNLOAD_BASE_URL="https://awscli.amazonaws.com"

# Distribution-source identifier used in three places: the download query
# string (for backend access-log attribution), the metadata.json
# distribution_source field, and the runtime user-agent. Keep these aligned
# so download logs, install metadata, and runtime telemetry correlate.
readonly DOWNLOAD_QUERY="?src=script-exe"

# Apple Developer Team identifier for AWS-signed PKGs (AMZN Mobile LLC).
# Pinning the team ID prevents any other Apple Developer ID from passing the
# macOS signature check.
readonly AWS_CLI_PKG_TEAM_ID="94KV3E626L"

# AWS CLI signing key for Linux .sig verification.
# Fingerprint: FB5D B77F D5C1 18B8 0511 ADA8 A631 0ACC 4672 475C
# Expires 2026-07-07 — must be rotated before then.
readonly AWS_CLI_PGP_KEY='-----BEGIN PGP PUBLIC KEY BLOCK-----

mQINBF2Cr7UBEADJZHcgusOJl7ENSyumXh85z0TRV0xJorM2B/JL0kHOyigQluUG
ZMLhENaG0bYatdrKP+3H91lvK050pXwnO/R7fB/FSTouki4ciIx5OuLlnJZIxSzx
PqGl0mkxImLNbGWoi6Lto0LYxqHN2iQtzlwTVmq9733zd3XfcXrZ3+LblHAgEt5G
TfNxEKJ8soPLyWmwDH6HWCnjZ/aIQRBTIQ05uVeEoYxSh6wOai7ss/KveoSNBbYz
gbdzoqI2Y8cgH2nbfgp3DSasaLZEdCSsIsK1u05CinE7k2qZ7KgKAUIcT/cR/grk
C6VwsnDU0OUCideXcQ8WeHutqvgZH1JgKDbznoIzeQHJD238GEu+eKhRHcz8/jeG
94zkcgJOz3KbZGYMiTh277Fvj9zzvZsbMBCedV1BTg3TqgvdX4bdkhf5cH+7NtWO
lrFj6UwAsGukBTAOxC0l/dnSmZhJ7Z1KmEWilro/gOrjtOxqRQutlIqG22TaqoPG
fYVN+en3Zwbt97kcgZDwqbuykNt64oZWc4XKCa3mprEGC3IbJTBFqglXmZ7l9ywG
EEUJYOlb2XrSuPWml39beWdKM8kzr1OjnlOm6+lpTRCBfo0wa9F8YZRhHPAkwKkX
XDeOGpWRj4ohOx0d2GWkyV5xyN14p2tQOCdOODmz80yUTgRpPVQUtOEhXQARAQAB
tCFBV1MgQ0xJIFRlYW0gPGF3cy1jbGlAYW1hem9uLmNvbT6JAlQEEwEIAD4CGwMF
CwkIBwIGFQoJCAsCBBYCAwECHgECF4AWIQT7Xbd/1cEYuAURraimMQrMRnJHXAUC
aGveYQUJDMpiLAAKCRCmMQrMRnJHXKBYD/9Ab0qQdGiO5hObchG8xh8Rpb4Mjyf6
0JrVo6m8GNjNj6BHkSc8fuTQJ/FaEhaQxj3pjZ3GXPrXjIIVChmICLlFuRXYzrXc
Pw0lniybypsZEVai5kO0tCNBCCFuMN9RsmmRG8mf7lC4FSTbUDmxG/QlYK+0IV/l
uJkzxWa+rySkdpm0JdqumjegNRgObdXHAQDWlubWQHWyZyIQ2B4U7AxqSpcdJp6I
S4Zds4wVLd1WE5pquYQ8vS2cNlDm4QNg8wTj58e3lKN47hXHMIb6CHxRnb947oJa
pg189LLPR5koh+EorNkA1wu5mAJtJvy5YMsppy2y/kIjp3lyY6AmPT1posgGk70Z
CmToEZ5rbd7ARExtlh76A0cabMDFlEHDIK8RNUOSRr7L64+KxOUegKBfQHb9dADY
qqiKqpCbKgvtWlds909Ms74JBgr2KwZCSY1HaOxnIr4CY43QRqAq5YHOay/mU+6w
hhmdF18vpyK0vfkvvGresWtSXbag7Hkt3XjaEw76BzxQH21EBDqU8WJVjHgU6ru+
DJTs+SxgJbaT3hb/vyjlw0lK+hFfhWKRwgOXH8vqducF95NRSUxtS4fpqxWVaw3Q
V2OWSjbne99A5EPEySzryFTKbMGwaTlAwMCwYevt4YT6eb7NmFhTx0Fis4TalUs+
j+c7Kg92pDx2uQ==
=OBAt
-----END PGP PUBLIC KEY BLOCK-----'

ARG_VERSION=""
ARG_SYSTEM=0
ARG_QUIET=0

PLATFORM=""
ARCH=""
INSTALL_DIR=""
BIN_DIR=""
TEMP_DIR=""
INSTALLER_PATH=""
PRE_INSTALL_VERSION=""
POST_INSTALL_VERSION=""

# stdout carries informational output and is silenced by --quiet.
# stderr carries warnings and errors and is never silenced.
info() {
  if [ "$ARG_QUIET" -eq 0 ]; then
    printf '%s\n' "$*"
  fi
}

warn() {
  printf 'aws-cli installer: warning: %s\n' "$*" >&2
}

error() {
  local code="$1"
  shift
  printf 'aws-cli installer: error: %s\n' "$*" >&2
  exit "$code"
}

print_help() {
  cat <<'EOF'
Usage: install.sh [OPTIONS]

Install or update the AWS CLI v2.

Options:
  --version <X.Y.Z>   Install a specific fully-qualified version (e.g. 2.27.41).
                      When omitted, installs the latest release.
  -s, --system        Install system-wide (requires root). Overrides XDG paths
                      and uses /usr/local/aws-cli + /usr/local/bin.
  -q, --quiet         Suppress non-essential output. Errors and warnings are
                      still printed to stderr.
  -h, --help          Show this help and exit.

Environment:
  XDG_DATA_HOME       Install root for user-local installs.
                      Default: $HOME/.local/share
  XDG_BIN_HOME        Symlink directory for user-local installs.
                      Default: $HOME/.local/bin
EOF
}

is_valid_semver() {
  case "$1" in
    [0-9]*.[0-9]*.[0-9]*)
      case "$1" in
        *[!0-9.]*) return 1 ;;
        *) return 0 ;;
      esac
      ;;
    *) return 1 ;;
  esac
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --version)
        [ $# -ge 2 ] || error 2 "--version requires a value"
        ARG_VERSION="$2"
        shift 2
        ;;
      --version=*)
        ARG_VERSION="${1#--version=}"
        shift
        ;;
      -s|--system)
        ARG_SYSTEM=1
        shift
        ;;
      -q|--quiet)
        ARG_QUIET=1
        shift
        ;;
      -h|--help)
        print_help
        exit 0
        ;;
      --)
        if [ $# -gt 1 ]; then
          shift
          error 2 "unexpected positional argument: $1"
        fi
        shift
        ;;
      *)
        error 2 "unknown argument: $1"
        ;;
    esac
  done

  if [ -n "$ARG_VERSION" ] && ! is_valid_semver "$ARG_VERSION"; then
    error 2 "--version must be fully-qualified semver (e.g. 2.27.41), got: $ARG_VERSION"
  fi
}

detect_platform() {
  local uname_s uname_m
  uname_s="$(uname -s)"
  uname_m="$(uname -m)"

  case "$uname_s" in
    Linux)  PLATFORM="linux" ;;
    Darwin) PLATFORM="macos" ;;
    *) error 1 "unsupported OS '$uname_s'. This script supports only Linux and macOS." ;;
  esac

  if [ "$PLATFORM" = "linux" ]; then
    case "$uname_m" in
      x86_64|amd64)  ARCH="x86_64" ;;
      aarch64|arm64) ARCH="aarch64" ;;
      *) error 1 "unsupported architecture '$uname_m' on Linux. AWS CLI v2 only ships x86_64 and aarch64 binaries." ;;
    esac
  fi
}

check_dependencies() {
  local missing=()
  local required=(curl mktemp uname)
  case "$PLATFORM" in
    linux) required+=(unzip) ;;
    macos) required+=(installer pkgutil) ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac

  local cmd
  for cmd in "${required[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing+=("$cmd")
    fi
  done

  if [ ${#missing[@]} -gt 0 ]; then
    error 1 "missing required dependencies: ${missing[*]}. Install them via your package manager and re-run."
  fi
}

# AWS CLI v2 binaries link against glibc and silently fail on musl. Probing
# for the musl loader is the only reliable signal; we let other libc
# variants (which are vanishingly rare) fail loudly downstream.
check_libc() {
  [ "$PLATFORM" = "linux" ] || return 0
  if compgen -G '/lib/ld-musl-*' >/dev/null 2>&1 || \
     compgen -G '/lib64/ld-musl-*' >/dev/null 2>&1; then
    error 1 "musl-based Linux detected. AWS CLI v2 binaries require glibc; install from source instead. See https://github.com/aws/aws-cli/blob/v2/CONTRIBUTING.md for source-install guidance."
  fi
}

check_system_privilege() {
  [ "$ARG_SYSTEM" -eq 1 ] || return 0
  if [ "$(id -u)" -ne 0 ]; then
    error 1 "--system requires root. Re-run with sudo, or omit --system for a user-local install."
  fi
}

# The macOS `installer` command fails on whitespace in install paths.
# Apply uniformly so the failure mode is the same on both platforms.
require_no_whitespace() {
  local label="$1" value="$2"
  case "$value" in
    *[[:space:]]*)
      error 2 "$label must not contain whitespace; got: '$value'"
      ;;
  esac
}

resolve_paths() {
  if [ "$ARG_SYSTEM" -eq 1 ]; then
    INSTALL_DIR="/usr/local/aws-cli"
    BIN_DIR="/usr/local/bin"
    return
  fi

  if [ -z "${HOME:-}" ]; then
    if [ -z "${XDG_DATA_HOME:-}" ] || [ -z "${XDG_BIN_HOME:-}" ]; then
      error 2 "HOME is not set; either set HOME, set both XDG_DATA_HOME and XDG_BIN_HOME, or pass --system."
    fi
  fi

  local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  local bin_home="${XDG_BIN_HOME:-$HOME/.local/bin}"

  require_no_whitespace "XDG_DATA_HOME (or its default)" "$data_home"
  require_no_whitespace "XDG_BIN_HOME (or its default)" "$bin_home"

  data_home="${data_home%/}"
  bin_home="${bin_home%/}"

  INSTALL_DIR="$data_home/aws-cli"
  BIN_DIR="$bin_home"
}

# Best-effort metadata.json probe across either install layout (flat for
# macOS PKG, v2/current for Linux). Used only for human-readable warnings.
read_distribution_source() {
  local install_root="$1"
  local meta
  for meta in \
        "$install_root/awscli/data/metadata.json" \
        "$install_root/v2/current/awscli/data/metadata.json"; do
    [ -f "$meta" ] || continue
    local line
    line="$(grep -o '"distribution_source"[[:space:]]*:[[:space:]]*"[^"]*"' "$meta" 2>/dev/null | head -n1)"
    if [ -n "$line" ]; then
      printf '%s' "$line" | sed -E 's/.*"distribution_source"[[:space:]]*:[[:space:]]*"([^"]*)".*/\1/'
      return 0
    fi
  done
  return 1
}

install_root_looks_present() {
  local root="$1"
  [ -e "$root/v2/current/bin/aws" ] || [ -e "$root/aws" ]
}

warn_existing_install() {
  local other_root other_label
  if [ "$ARG_SYSTEM" -eq 1 ]; then
    if [ -z "${HOME:-}" ] && [ -z "${XDG_DATA_HOME:-}" ]; then
      return
    fi
    other_root="${XDG_DATA_HOME:-$HOME/.local/share}/aws-cli"
    other_label="user-local"
  else
    other_root="/usr/local/aws-cli"
    other_label="system-wide"
  fi

  if install_root_looks_present "$other_root"; then
    local src
    if src="$(read_distribution_source "$other_root" 2>/dev/null)" && [ -n "$src" ]; then
      warn "existing $other_label AWS CLI install found at $other_root (distribution_source=$src). Both installs will coexist; PATH precedence will determine which 'aws' runs."
    else
      warn "existing $other_label AWS CLI install found at $other_root. Both installs will coexist; PATH precedence will determine which 'aws' runs."
    fi
  fi
}

cleanup() {
  local rc=$?
  if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
    if ! rm -rf "$TEMP_DIR" 2>/dev/null; then
      warn "could not remove temp directory: $TEMP_DIR"
    fi
  fi
  exit "$rc"
}

setup_temp_dir() {
  TEMP_DIR="$(mktemp -d 2>/dev/null)" || error 1 "failed to create temp directory via mktemp -d"
  trap cleanup EXIT INT TERM
}

installer_filename() {
  case "$PLATFORM" in
    linux)
      if [ -n "$ARG_VERSION" ]; then
        printf 'awscli-exe-linux-%s-%s.zip' "$ARCH" "$ARG_VERSION"
      else
        printf 'awscli-exe-linux-%s.zip' "$ARCH"
      fi
      ;;
    macos)
      if [ -n "$ARG_VERSION" ]; then
        printf 'AWSCLIV2-%s.pkg' "$ARG_VERSION"
      else
        printf 'AWSCLIV2.pkg'
      fi
      ;;
    *) error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

build_installer_url() {
  printf '%s/%s%s' "$DOWNLOAD_BASE_URL" "$(installer_filename)" "$DOWNLOAD_QUERY"
}

build_signature_url() {
  printf '%s/%s.sig%s' "$DOWNLOAD_BASE_URL" "$(installer_filename)" "$DOWNLOAD_QUERY"
}

curl_to_file() {
  local url="$1" out="$2"
  local progress_flag="--progress-bar"
  if [ "$ARG_QUIET" -eq 1 ]; then
    progress_flag="--silent"
  fi
  curl --fail --location --show-error "$progress_flag" \
       --connect-timeout 10 --retry 0 \
       --output "$out" "$url"
}

download_with_retry() {
  local url="$1" out="$2" label="$3"
  info "Downloading $label from $url"
  if curl_to_file "$url" "$out"; then
    return 0
  fi
  warn "download of $label failed; retrying once"
  if curl_to_file "$url" "$out"; then
    return 0
  fi
  error 1 "failed to download $label from $url after one retry"
}

download_installer() {
  local url ext
  url="$(build_installer_url)"
  case "$PLATFORM" in
    linux) ext="zip" ;;
    macos) ext="pkg" ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
  INSTALLER_PATH="$TEMP_DIR/awscliv2.$ext"
  download_with_retry "$url" "$INSTALLER_PATH" "AWS CLI installer"
}

verify_linux_signature() {
  if ! command -v gpg >/dev/null 2>&1; then
    warn "gpg not found; skipping signature verification. Install gnupg for stronger integrity guarantees."
    return 0
  fi

  local sig_url sig_path gpghome keyfile
  sig_url="$(build_signature_url)"
  sig_path="$TEMP_DIR/awscliv2.sig"
  # Isolated GPG home avoids touching the user's keyring/trustdb. --homedir
  # is the modern equivalent of --no-default-keyring --keyring <file>; the
  # latter triggers spurious "Need the secret key" warnings on GPG 2.1+.
  gpghome="$TEMP_DIR/gpghome"
  keyfile="$TEMP_DIR/aws-cli.key"

  download_with_retry "$sig_url" "$sig_path" "AWS CLI signature"

  mkdir -m 700 "$gpghome" || error 1 "failed to create GPG home directory"
  printf '%s\n' "$AWS_CLI_PGP_KEY" > "$keyfile"

  # --no-autostart prevents gpg from launching gpg-agent, which is missing
  # on minimal images (e.g., Amazon Linux base). Neither --import nor
  # --verify needs the agent.
  local gpg_opts=(--homedir "$gpghome" --batch --no-autostart)

  # Don't gate on the import's exit code: it returns non-zero on minimal
  # systems even after a successful import (missing gpg-agent, key
  # preference warnings). If the import truly failed, --verify below will
  # report "No public key" and we'll surface that error.
  gpg "${gpg_opts[@]}" --import "$keyfile" >/dev/null 2>&1 || true

  local verify_out
  if ! verify_out="$(gpg "${gpg_opts[@]}" \
        --verify "$sig_path" "$INSTALLER_PATH" 2>&1)"; then
    error 1 "GPG signature verification failed for $INSTALLER_PATH:"$'\n'"$verify_out"
  fi

  info "GPG signature verified."
}

verify_macos_signature() {
  if ! command -v pkgutil >/dev/null 2>&1; then
    warn "pkgutil not found; skipping signature verification"
    return 0
  fi

  # Two checks must both pass: the package must be Apple-Developer-ID-signed,
  # and the leaf certificate must carry our team identifier — otherwise any
  # other Apple Developer account could ship a PKG that satisfies the first
  # check.
  local out
  if ! out="$(pkgutil --check-signature "$INSTALLER_PATH" 2>&1)"; then
    error 1 "pkgutil signature verification failed for $INSTALLER_PATH:"$'\n'"$out"
  fi
  case "$out" in
    *"signed by a developer certificate issued by Apple for distribution"*) ;;
    *) error 1 "downloaded PKG is not signed by an Apple Developer ID. Refusing to install." ;;
  esac
  case "$out" in
    *"($AWS_CLI_PKG_TEAM_ID)"*) ;;
    *) error 1 "downloaded PKG is signed by an unexpected Apple Developer team (expected $AWS_CLI_PKG_TEAM_ID, AMZN Mobile LLC). Refusing to install." ;;
  esac

  info "PKG code signature verified (team $AWS_CLI_PKG_TEAM_ID)."
}

verify_installer() {
  case "$PLATFORM" in
    linux) verify_linux_signature ;;
    macos) verify_macos_signature ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

read_installed_version() {
  local aws_bin="$1"
  [ -x "$aws_bin" ] || return 1
  local out
  out="$("$aws_bin" --version 2>/dev/null)" || return 1
  printf '%s\n' "$out" | sed -nE 's#^aws-cli/([0-9]+\.[0-9]+\.[0-9]+).*#\1#p' | head -n1
}

# macOS PKG layout (system or user-local) is flat: $INSTALL_DIR/aws.
# Linux ./aws/install creates a versioned tree with a 'current' symlink.
candidate_aws_binary() {
  case "$PLATFORM" in
    macos) printf '%s/aws' "$INSTALL_DIR" ;;
    linux) printf '%s/v2/current/bin/aws' "$INSTALL_DIR" ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

capture_pre_install_version() {
  local aws_bin
  aws_bin="$(candidate_aws_binary)"
  PRE_INSTALL_VERSION="$(read_installed_version "$aws_bin" || true)"
}

run_linux_installer() {
  ( cd "$TEMP_DIR" && unzip -o -q "$INSTALLER_PATH" )

  mkdir -p "$BIN_DIR" || error 7 "could not create $BIN_DIR"
  if [ "$ARG_SYSTEM" -eq 0 ]; then
    mkdir -p "$INSTALL_DIR" || error 7 "could not create $INSTALL_DIR"
  fi

  # The bundled installer requires --update when an install already exists.
  local update_flag=""
  if [ -e "$(candidate_aws_binary)" ]; then
    update_flag="--update"
  fi

  if [ "$ARG_SYSTEM" -eq 1 ]; then
    "$TEMP_DIR/aws/install" $update_flag \
      || error 8 "AWS CLI installer failed"
  else
    "$TEMP_DIR/aws/install" \
      --install-dir "$INSTALL_DIR" \
      --bin-dir "$BIN_DIR" \
      $update_flag \
      || error 8 "AWS CLI installer failed"
  fi
}

run_macos_installer() {
  if [ "$ARG_SYSTEM" -eq 1 ]; then
    installer -pkg "$INSTALLER_PATH" -target / \
      || error 8 "AWS CLI installer failed"
    return
  fi

  # The PKG always creates an "aws-cli" folder inside its customLocation, so
  # we pass the parent of $INSTALL_DIR (which itself ends in "aws-cli").
  local install_parent
  install_parent="$(dirname "$INSTALL_DIR")"
  mkdir -p "$install_parent" || error 7 "could not create $install_parent"
  mkdir -p "$BIN_DIR"        || error 7 "could not create $BIN_DIR"

  local choices="$TEMP_DIR/choices.xml"
  cat > "$choices" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <array>
    <dict>
      <key>choiceAttribute</key>
      <string>customLocation</string>
      <key>attributeSetting</key>
      <string>$install_parent</string>
      <key>choiceIdentifier</key>
      <string>default</string>
    </dict>
  </array>
</plist>
EOF

  installer -pkg "$INSTALLER_PATH" \
            -target CurrentUserHomeDirectory \
            -applyChoiceChangesXML "$choices" \
    || error 8 "AWS CLI installer failed"

  # The user-local PKG mode does not create symlinks for us.
  ln -sf "$INSTALL_DIR/aws"           "$BIN_DIR/aws"
  ln -sf "$INSTALL_DIR/aws_completer" "$BIN_DIR/aws_completer"
}

run_installer() {
  case "$PLATFORM" in
    linux) run_linux_installer ;;
    macos) run_macos_installer ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

verify_install_runs() {
  local aws_bin
  aws_bin="$(candidate_aws_binary)"
  POST_INSTALL_VERSION="$(read_installed_version "$aws_bin" || true)"
  if [ -z "$POST_INSTALL_VERSION" ]; then
    error 9 "post-install check failed: '$aws_bin --version' did not run successfully."
  fi
}

emit_already_installed_warning() {
  if [ -n "$PRE_INSTALL_VERSION" ] && \
     [ "$PRE_INSTALL_VERSION" = "$POST_INSTALL_VERSION" ]; then
    warn "AWS CLI $POST_INSTALL_VERSION is already installed at $INSTALL_DIR; nothing to update."
  fi
}

# Best-effort: never fail the script over metadata. Uses python3 if
# available; silently no-ops otherwise.
write_metadata() {
  local install_tree
  case "$PLATFORM" in
    macos) install_tree="$INSTALL_DIR" ;;
    linux) install_tree="$INSTALL_DIR/v2/current" ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
  local meta="$install_tree/awscli/data/metadata.json"
  [ -f "$meta" ] || return 0

  local version_requested
  if [ -n "$ARG_VERSION" ]; then
    version_requested="$ARG_VERSION"
  else
    version_requested="latest"
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$meta" "$INSTALL_DIR" "$BIN_DIR" \
            "$ARG_SYSTEM" "$version_requested" "$POST_INSTALL_VERSION" \
            "$ARG_QUIET" "$SCRIPT_VERSION" <<'PY' || return 0
import json, sys
meta_path = sys.argv[1]
with open(meta_path) as f:
    data = json.load(f)
data["distribution_source"] = "script-exe"
data["script_install"] = {
    "install_dir": sys.argv[2],
    "bin_dir": sys.argv[3],
    "system": sys.argv[4] == "1",
    "version_requested": sys.argv[5],
    "version_resolved": sys.argv[6],
    "quiet": sys.argv[7] == "1",
    "script_version": sys.argv[8],
}
with open(meta_path, "w") as f:
    json.dump(data, f, indent=2)
PY
  fi
}

check_path_precedence() {
  local resolved
  resolved="$(command -v aws 2>/dev/null || true)"
  [ -n "$resolved" ] || return 1
  local resolved_real expected_real
  resolved_real="$(readlink -f "$resolved" 2>/dev/null || printf '%s' "$resolved")"
  expected_real="$(readlink -f "$(candidate_aws_binary)" 2>/dev/null || candidate_aws_binary)"
  [ "$resolved_real" = "$expected_real" ]
}

print_path_warning() {
  local shell_name snippet
  shell_name="$(basename "${SHELL:-}")"
  case "$shell_name" in
    bash) snippet="echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc" ;;
    zsh)  snippet="echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc" ;;
    fish) snippet="fish_add_path $BIN_DIR" ;;
    *)    snippet="export PATH=\"$BIN_DIR:\$PATH\"  # add this line to your shell startup file" ;;
  esac
  warn "$BIN_DIR is not first on PATH. The 'aws' command may resolve to a different install."
  warn "To fix, run:"$'\n'"  $snippet"
  warn "Then start a new shell session."
}

post_install_checks() {
  verify_install_runs
  emit_already_installed_warning
  write_metadata
  if ! check_path_precedence; then
    print_path_warning
  fi
  info "AWS CLI $POST_INSTALL_VERSION installed to $INSTALL_DIR"
}

main() {
  parse_args "$@"
  detect_platform
  check_dependencies
  check_libc
  check_system_privilege
  resolve_paths
  warn_existing_install

  setup_temp_dir
  capture_pre_install_version
  download_installer
  verify_installer
  run_installer
  post_install_checks
}

main "$@"
