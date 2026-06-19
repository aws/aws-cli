#!/usr/bin/env bash
#
# AWS CLI v2 install script for Linux and macOS.
#
# Defaults to a user-local install under XDG paths. Use --system for the
# traditional /usr/local layout (requires root). See --help for details.

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

readonly DOWNLOAD_BASE_URL="https://awscli.amazonaws.com"
readonly LATEST_VERSION_URL="${DOWNLOAD_BASE_URL}/v2/version.txt"

readonly DISTRIBUTION_SOURCE="${AWS_CLI_DISTRIBUTION_SOURCE_OVERRIDE:-script-exe}"
readonly DOWNLOAD_QUERY="?src=${DISTRIBUTION_SOURCE}"

readonly SYSTEM_INSTALL_DIR="/usr/local/aws-cli"
readonly SYSTEM_BIN_DIR="/usr/local/bin"

readonly AWS_CLI_PKG_TEAM_ID="94KV3E626L"

# AWS CLI public signing key, used to verify the Linux .sig.
# Fingerprint: FB5D B77F D5C1 18B8 0511 ADA8 A631 0ACC 4672 475C
# Expires 2026-07-07.
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

# ----- Parsed arguments (set by parse_args) ---------------------------------
ARG_VERSION=""            # --version value, empty means "latest"
ARG_SYSTEM=0              # 1 if --system
ARG_QUIET=0               # 1 if --quiet

# ----- Resolved state (set at runtime) --------------------------------------
PLATFORM=""               # "linux" | "macos"
ARCH=""                   # "x86_64" | "aarch64"
INSTALL_DIR=""            # install root (layout differs per platform)
BIN_DIR=""                # symlink dir for aws/aws_completer
TEMP_DIR=""               # working dir from mktemp -d; removed by cleanup trap
INSTALLER_PATH=""         # downloaded zip/pkg path
PRE_INSTALL_VERSION=""    # version present before install
POST_INSTALL_VERSION=""   # version present after install
TARGET_VERSION=""         # version we resolved to install

COLOR_RED=""
COLOR_YELLOW=""
COLOR_GREEN=""
COLOR_RESET=""

# ============================================================================
# Output helpers
# ============================================================================

# Enable color unless NO_COLOR is set or TERM is dumb.
setup_colors() {
  [ -z "${NO_COLOR:-}" ] || return 0
  [ "${TERM:-}" != "dumb" ] || return 0
  COLOR_RED=$'\033[31m'
  COLOR_YELLOW=$'\033[33m'
  COLOR_GREEN=$'\033[32m'
  COLOR_RESET=$'\033[0m'
}

# Progress/info on stdout, silenced by --quiet.
info() {
  if [ "$ARG_QUIET" -eq 0 ]; then
    printf '%s\n' "$*"
  fi
}

# Green success on stdout, silenced by --quiet.
success() {
  [ "$ARG_QUIET" -eq 0 ] || return 0
  if [ -t 1 ]; then
    printf '%s%s%s\n' "$COLOR_GREEN" "$*" "$COLOR_RESET"
  else
    printf '%s\n' "$*"
  fi
}

# Yellow warning on stderr; never silenced.
warn() {
  if [ -t 2 ]; then
    printf '%saws-cli installer: warning:%s %s\n' "$COLOR_YELLOW" "$COLOR_RESET" "$*" >&2
  else
    printf 'aws-cli installer: warning: %s\n' "$*" >&2
  fi
}

# Red error on stderr, then exit with the given code; never silenced.
error() {
  local code="$1"
  shift
  if [ -t 2 ]; then
    printf '%saws-cli installer: error:%s %s\n' "$COLOR_RED" "$COLOR_RESET" "$*" >&2
  else
    printf 'aws-cli installer: error: %s\n' "$*" >&2
  fi
  exit "$code"
}

# ============================================================================
# Argument parsing
# ============================================================================

print_help() {
  cat <<'EOF'
Usage: install.sh [OPTIONS]

Install the AWS CLI v2.

Options:
  --version <X.Y.Z>   Install a specific fully-qualified version (e.g. 2.27.41).
                      When omitted, installs the latest release. Downgrades
                      are not supported. To install a previous version, see:
                      https://docs.aws.amazon.com/cli/latest/userguide/getting-started-version.html
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

# Accept only fully-qualified MAJOR.MINOR.PATCH.
is_valid_semver() {
  [[ "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]
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
        [ -n "$ARG_VERSION" ] || error 2 "--version requires a value"
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
        # End of options. The script takes no positional args, so anything
        # after -- is unexpected.
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

# ============================================================================
# Pre-install checks
# ============================================================================

# Sets PLATFORM and ARCH.
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

# gpg is not strictly required because it's not uncommon for Linux distributions
# to lack them by default.
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

# AWS CLI v2 Linux binaries are built and tested against glibc.
check_libc() {
  [ "$PLATFORM" = "linux" ] || return 0
  if compgen -G '/lib/ld-musl-*' >/dev/null 2>&1 || \
     compgen -G '/lib64/ld-musl-*' >/dev/null 2>&1; then
    error 1 "musl-based Linux detected. AWS CLI v2 binaries require glibc; install from source instead. See https://docs.aws.amazon.com/cli/latest/userguide/getting-started-source-install.html"
  fi
}

check_system_privilege() {
  [ "$ARG_SYSTEM" -eq 1 ] || return 0
  if [ "$(id -u)" -ne 0 ]; then
    error 1 "--system requires root. Re-run with sudo, or omit --system for a user-local install."
  fi
}

# ============================================================================
# Path resolution
# ============================================================================

# The macOS `installer` command fails on whitespace in install paths, so we
# reject it up front on both platforms for a consistent failure mode.
require_no_whitespace() {
  local label="$1" value="$2"
  case "$value" in
    *[[:space:]]*)
      error 2 "$label must not contain whitespace; got: '$value'"
      ;;
  esac
}

# Resolves INSTALL_DIR and BIN_DIR. System mode uses the fixed /usr/local
# layout; user-local mode follows the XDG base-dir spec.
resolve_paths() {
  if [ "$ARG_SYSTEM" -eq 1 ]; then
    INSTALL_DIR="$SYSTEM_INSTALL_DIR"
    BIN_DIR="$SYSTEM_BIN_DIR"
    return
  fi

  # User-local defaults derive from HOME. Allow HOME to be unset only if both
  # XDG vars are explicitly provided.
  if [ -z "${HOME:-}" ]; then
    if [ -z "${XDG_DATA_HOME:-}" ] || [ -z "${XDG_BIN_HOME:-}" ]; then
      error 2 "HOME is not set; either set HOME, set both XDG_DATA_HOME and XDG_BIN_HOME, or pass --system."
    fi
  fi

  local data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
  local bin_home="${XDG_BIN_HOME:-$HOME/.local/bin}"

  require_no_whitespace "XDG_DATA_HOME (or its default)" "$data_home"
  require_no_whitespace "XDG_BIN_HOME (or its default)" "$bin_home"

  # Strip trailing slashes so path joins below stay clean.
  data_home="${data_home%/}"
  bin_home="${bin_home%/}"

  INSTALL_DIR="$data_home/aws-cli"
  BIN_DIR="$bin_home"

  info "Resolving user-local install paths:"
  info "  HOME=${HOME:-<unset>}"
  info "  XDG_DATA_HOME=${XDG_DATA_HOME:-<unset, using default>}"
  info "  XDG_BIN_HOME=${XDG_BIN_HOME:-<unset, using default>}"

  # Running as root without --system installs into root's own home rather than
  # the invoking user's. If root was entered via sudo, any HOME or
  # XDG_DATA_HOME/XDG_BIN_HOME set in the calling user's shell were dropped
  # (sudo does not inherit them by default), so the paths above may not be
  # where the user expected.
  if [ "$(id -u)" -eq 0 ]; then
    warn "running as root without --system; installing to $INSTALL_DIR with binaries in $BIN_DIR. If you used sudo, it may have reset environment variables like HOME and XDG_DATA_HOME/XDG_BIN_HOME."
  fi
}

# ============================================================================
# Download
# ============================================================================

# EXIT/INT/TERM trap: remove the temp dir on any exit while preserving the
# original exit code.
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
      if [ -n "$TARGET_VERSION" ]; then
        printf 'awscli-exe-linux-%s-%s.zip' "$ARCH" "$TARGET_VERSION"
      else
        printf 'awscli-exe-linux-%s.zip' "$ARCH"
      fi
      ;;
    macos)
      if [ -n "$TARGET_VERSION" ]; then
        printf 'AWSCLIV2-%s.pkg' "$TARGET_VERSION"
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

# ============================================================================
# Signature verification
# ============================================================================

verify_linux_signature() {
  if ! command -v gpg >/dev/null 2>&1; then
    warn "gpg not found; skipping signature verification. Install gnupg for stronger integrity guarantees."
    return 0
  fi

  local sig_url sig_path gpghome keyfile
  sig_url="$(build_signature_url)"
  sig_path="$TEMP_DIR/awscliv2.sig"
  gpghome="$TEMP_DIR/gpghome"     # isolated keyring; never touches user's ~/.gnupg
  keyfile="$TEMP_DIR/aws-cli.key"

  download_with_retry "$sig_url" "$sig_path" "AWS CLI signature"

  mkdir -m 700 "$gpghome" || error 1 "failed to create GPG home directory"
  printf '%s\n' "$AWS_CLI_PGP_KEY" > "$keyfile"

  local gpg_opts=(--homedir "$gpghome" --batch --no-autostart)
  # Import can exit non-zero on minimal systems even when it succeeds (key
  # preference warnings, missing agent), so capture it and judge by --verify.
  local import_out
  import_out="$(gpg "${gpg_opts[@]}" --import "$keyfile" 2>&1)" || true

  local verify_out
  if ! verify_out="$(gpg "${gpg_opts[@]}" \
        --verify "$sig_path" "$INSTALLER_PATH" 2>&1)"; then
    if ! echo "$import_out" | grep -q 'imported'; then
      error 1 "failed to import AWS CLI signing key into temporary keyring:"$'\n'"$import_out"
    fi
    error 1 "GPG signature verification failed for $INSTALLER_PATH:"$'\n'"$verify_out"
  fi

  success "GPG signature verified."
}

verify_macos_signature() {
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

  success "PKG code signature verified (team $AWS_CLI_PKG_TEAM_ID)."
}

verify_installer() {
  case "$PLATFORM" in
    linux) verify_linux_signature ;;
    macos) verify_macos_signature ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

# ============================================================================
# Version resolution
# ============================================================================

# Extracts the semver from `aws --version` output.
read_installed_version() {
  local aws_bin="$1"
  [ -x "$aws_bin" ] || return 1
  local out
  out="$("$aws_bin" --version 2>/dev/null)" || return 1
  printf '%s\n' "$out" | sed -nE 's#^aws-cli/([0-9]+\.[0-9]+\.[0-9]+).*#\1#p' | head -n1
}

# Path to the installed aws binary. macOS PKG lays out a flat dir; the Linux
# installer uses a versioned tree with a 'current' symlink.
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

fetch_latest_version() {
  local out
  out="$(curl --fail --silent --show-error --location \
              --connect-timeout 10 --retry 0 \
              "$LATEST_VERSION_URL" 2>/dev/null || true)"
  out="$(printf '%s' "$out" | tr -d '[:space:]')"
  is_valid_semver "$out" && printf '%s' "$out"
}

lower_version() {
  printf '%s\n%s\n' "$1" "$2" | sort -V | head -n1
}

# Resolves TARGET_VERSION, short-circuits when nothing needs to happen.
resolve_target_and_announce() {
  if [ -n "$ARG_VERSION" ]; then
    TARGET_VERSION="$ARG_VERSION"
  else
    TARGET_VERSION="$(fetch_latest_version)"
  fi

  if [ -z "$TARGET_VERSION" ] || [ -z "$PRE_INSTALL_VERSION" ]; then
    [ -n "$TARGET_VERSION" ] && info "Installing AWS CLI $TARGET_VERSION"
    return
  fi

  if [ "$PRE_INSTALL_VERSION" = "$TARGET_VERSION" ]; then
    info "AWS CLI $TARGET_VERSION is already installed at $INSTALL_DIR; nothing to do."
    exit 0
  fi

  if [ "$(lower_version "$PRE_INSTALL_VERSION" "$TARGET_VERSION")" = "$TARGET_VERSION" ]; then
    info "AWS CLI $PRE_INSTALL_VERSION is already installed at $INSTALL_DIR. To install $TARGET_VERSION, uninstall the existing AWS CLI at $INSTALL_DIR and try again."
    exit 0
  fi

  info "Installing AWS CLI $PRE_INSTALL_VERSION → $TARGET_VERSION"
}

# ============================================================================
# Install
# ============================================================================

run_linux_installer() {
  ( cd "$TEMP_DIR" && unzip -o -q "$INSTALLER_PATH" )

  mkdir -p "$BIN_DIR" || error 7 "could not create $BIN_DIR"
  if [ "$ARG_SYSTEM" -eq 0 ]; then
    mkdir -p "$INSTALL_DIR" || error 7 "could not create $INSTALL_DIR"
  fi

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

  local install_parent
  install_parent="$(dirname "$INSTALL_DIR")"
  mkdir -p "$install_parent" || error 7 "could not create $install_parent"
  mkdir -p "$BIN_DIR"        || error 7 "could not create $BIN_DIR"

  # Reject paths with XML-special characters that would break choices.xml.
  case "$install_parent" in
    *\&*|*\<*|*\>*|*\"*|*\'*)
      error 2 "install path contains characters that are not supported: '$install_parent'"
      ;;
  esac

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

  ln -sf "$INSTALL_DIR/aws"           "$BIN_DIR/aws"
  ln -sf "$INSTALL_DIR/aws_completer" "$BIN_DIR/aws_completer"
}

run_installer() {
  # Tell the bundled installer not to write install.json.
  export AWS_CLI_SKIP_INSTALL_JSON=1
  case "$PLATFORM" in
    linux) run_linux_installer ;;
    macos) run_macos_installer ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
}

# ============================================================================
# Post-install
# ============================================================================

verify_install_runs() {
  local aws_bin
  aws_bin="$(candidate_aws_binary)"
  POST_INSTALL_VERSION="$(read_installed_version "$aws_bin" || true)"
  if [ -z "$POST_INSTALL_VERSION" ]; then
    error 9 "post-install check failed: '$aws_bin --version' did not run successfully."
  fi
}

json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

# Writes install-time metadata next to the bundled metadata.json. `aws update`
# reads this back to learn where and how the CLI was installed.
write_install_json() {
  local install_json
  case "$PLATFORM" in
    macos) install_json="$INSTALL_DIR/awscli/data/install.json" ;;
    linux) install_json="$INSTALL_DIR/v2/current/dist/awscli/data/install.json" ;;
    *)     error 1 "internal error: unknown platform '$PLATFORM'" ;;
  esac
  [ -d "$(dirname "$install_json")" ] || return 0

  local system_b quiet_b
  if [ "$ARG_SYSTEM" -eq 1 ]; then system_b=true; else system_b=false; fi
  if [ "$ARG_QUIET"  -eq 1 ]; then quiet_b=true;  else quiet_b=false;  fi

  cat > "$install_json" <<EOF
{
  "distribution_source": "$(json_escape "$DISTRIBUTION_SOURCE")",
  "install_dir": "$(json_escape "$INSTALL_DIR")",
  "bin_dir": "$(json_escape "$BIN_DIR")",
  "script_install": {
    "system": $system_b,
    "version_resolved": "$(json_escape "$POST_INSTALL_VERSION")",
    "quiet": $quiet_b
  }
}
EOF
}

post_install_checks() {
  verify_install_runs
  write_install_json
  success "AWS CLI $POST_INSTALL_VERSION installed to $INSTALL_DIR"
  info "Ensure $BIN_DIR is on your PATH. When multiple installs exist, PATH order determines which 'aws' runs."
}

# ============================================================================
# Entry point
# ============================================================================

main() {
  setup_colors
  parse_args "$@"

  # Pre-flight: validate the environment before touching the network or disk.
  detect_platform
  check_dependencies
  check_libc
  check_system_privilege
  resolve_paths

  # Install: stage, resolve target, download, verify, run.
  setup_temp_dir
  capture_pre_install_version
  resolve_target_and_announce
  download_installer
  verify_installer
  run_installer
  post_install_checks
}

main "$@"
