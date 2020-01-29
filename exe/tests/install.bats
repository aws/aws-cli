#!/usr/bin/env bats

setup() {
  EXE_BUNDLE_DIR="$BATS_TMPDIR/aws"
  EXE_DIST_DIR="$EXE_BUNDLE_DIR/dist"
  AWS_EXE_VERSION="2.0.0dev0"
  new_exe_bundle "$AWS_EXE_VERSION"
  INSTALL_DIR="$BATS_TMPDIR/aws-cli"
  BIN_DIR="$BATS_TMPDIR/bin"
}

teardown() {
  clear_preexisting_bundle
  rm -rf "$INSTALL_DIR"
  rm -rf "$BIN_DIR"
}

new_exe_bundle() {
  aws_exe_version="$1"
  clear_preexisting_bundle
  mkdir -p "$EXE_BUNDLE_DIR"
  mkdir -p "$EXE_DIST_DIR"
  cp "${BATS_TEST_DIRNAME}/../assets/install" "$EXE_BUNDLE_DIR"
  create_exes "$aws_exe_version"
}

clear_preexisting_bundle() {
  [ -d "$EXE_BUNDLE_DIR" ] || rm -rf "$EXE_BUNDLE_DIR"
}

create_exes() {
  aws_exe_version="$1"
  aws_exe="$EXE_DIST_DIR/aws"
  aws_completer_exe="$EXE_DIST_DIR/aws_completer"

  aws_exe_contents="echo \"$(aws_version_output "$aws_exe_version")\""
  echo "$aws_exe_contents" > "$aws_exe"
  chmod +x "$aws_exe"

  touch "$aws_completer_exe"
  chmod +x "$aws_completer_exe"
}

aws_version_output() {
  echo "aws-cli/$1 Python/3.7.2 Darwin/17.7.0 botocore/1.12.48"
}

run_install() {
  run "$EXE_BUNDLE_DIR/install" "$@"
}

assert_expected_installation() {
  expected_installed_version="$1"
  expected_current_dir="$INSTALL_DIR/v2/current"
  expected_install_dir="$INSTALL_DIR/v2/$expected_installed_version"

  # Assert that the installation of the installed version is correct
  [ -d "$expected_install_dir" ]
  assert_expected_symlink "$expected_install_dir/bin/aws" "../dist/aws"
  assert_expected_symlink "$expected_install_dir/bin/aws_completer" "../dist/aws_completer"

  # Assert that current points to the expected installed version
  readlink "$expected_current_dir"
  assert_expected_symlink "$expected_current_dir" "$expected_install_dir"

  # Assert the bin symlinks are correct
  assert_expected_symlink "$BIN_DIR/aws" "$expected_current_dir/bin/aws"
  assert_expected_symlink "$BIN_DIR/aws_completer" "$expected_current_dir/bin/aws_completer"

  # Assert the executable works with the expected output
  [ "$("$BIN_DIR/aws" --version)" = "$(aws_version_output "$expected_installed_version")" ]
}

assert_expected_symlink() {
  expected_symlink="$1"
  expected_target="$2"
  [ -L "$expected_symlink" ]
  [ "$(readlink "$expected_symlink")" = "$expected_target" ]
}

@test "-h prints help" {
  run_install -h
  [[ "$output" = *"USAGE"* ]]
}

@test "--help prints help" {
  run_install -h
  [[ "$output" = *"USAGE"* ]]
}

@test "with unexpected arguments" {
  run_install --unexpected
  [ "$status" -eq 1 ]
  [[ "$output" = *"unexpected argument"* ]]
}

@test "install" {
  run_install --install-dir "$INSTALL_DIR" --bin-dir "$BIN_DIR"
  [ "$status" -eq 0 ]
  [ "$output" = "You can now run: $BIN_DIR/aws --version" ]
  assert_expected_installation "$AWS_EXE_VERSION"
}

@test "using shorthand parameters" {
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 0 ]
  [ "$output" = "You can now run: $BIN_DIR/aws --version" ]
  assert_expected_installation "$AWS_EXE_VERSION"
}

@test "fails when detects preexisting installation" {
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 0 ]

  new_exe_bundle "new-version"
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 1 ]
  [[ "$output" = *"Found preexisting"* ]]
}

@test "--updates updates to new version" {
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 0 ]

  new_exe_bundle "new-version"
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR" --update
  [ "$status" -eq 0 ]
  assert_expected_installation "new-version"
}

@test "-u updates to new version" {
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 0 ]

  new_exe_bundle "new-version"
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR" -u
  [ "$status" -eq 0 ]
  assert_expected_installation "new-version"
}

@test "--update skips for same version" {
  run_install -i "$INSTALL_DIR" -b "$BIN_DIR"
  [ "$status" -eq 0 ]

  run_install -i "$INSTALL_DIR" -b "$BIN_DIR" -u
  [ "$status" -eq 0 ]
  [[ "$output" = *"Found same AWS CLI version"* ]]
  assert_expected_installation "$AWS_EXE_VERSION"
}
