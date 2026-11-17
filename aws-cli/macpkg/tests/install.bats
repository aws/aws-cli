#!/usr/bin/env bats

setup() {
    if [ -z "$INSTALLER_TO_TEST" ]; then
	INSTALLER_TO_TEST="../../dist/AWS-CLI-Installer.pkg"
    fi
    PKG_PATH="$BATS_TMPDIR/installer.pkg"
    CHOICE_XML="$BATS_TMPDIR/choices.xml"
    INSTALL_TARGET="$HOME/.tmp-cli-pkg-test"
    mkdir -p "$INSTALL_TARGET"
    copy_pkg
}

teardown() {
    rm -rf "$INSTALL_TARGET"
}

copy_pkg() {
    cp "$INSTALLER_TO_TEST" "$PKG_PATH"
}

write_choices() {
    sed "s+REPLACEME+$1+g" > "$CHOICE_XML" < choices.xml
}

@test "user install with custom location succeeds" {
    write_choices "$INSTALL_TARGET"
    installer -target CurrentUserHomeDirectory -pkg "$PKG_PATH" -applyChoiceChangesXML "$CHOICE_XML"
    run "$INSTALL_TARGET/aws-cli/aws" "--version"
    [ "$status"  -eq 0 ]
}
