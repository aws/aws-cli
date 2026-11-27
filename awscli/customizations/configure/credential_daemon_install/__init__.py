# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""``aws configure credential-daemon install``, ``uninstall`` and ``link``.

``install`` downloads aws-credential-daemon's latest release from GitHub,
checks its signature, and runs its installer. Nothing is installed unless the
signature checks out: a detached PGP signature for the Linux archive, and
Apple's signature and notarization for the macOS package. Files come only from
the release whose tag gave the version. On macOS the signed package's own
version must match that tag. Installing changes no profile.

The AWS CLI and SDKs find the credential daemon at
``~/.aws/credential-daemon.sock`` (or ``AWS_CREDENTIAL_DAEMON_SOCKET``), so
``install`` also links that path to aws-credential-daemon's own socket, and
``link`` creates or removes the link for a user who didn't install.

``uninstall`` reverses what ``install`` put down: it runs
aws-credential-daemon's own uninstaller, then removes the files the install
added and the link. The credential daemon's saved sign-ins and keys stay, so
a reinstall brings them back, and nothing else in ~/.aws changes.

On macOS everything works for the current user only and refuses to run as
root: aws-credential-daemon's signed package installs only per user. On Linux
the system service needs root: ``install`` and ``uninstall`` run as a user
refuse, print the ``sudo`` command to run, and change nothing. Run under
sudo, they link or remove the link of root and of the user who ran sudo,
the latter as that user.
"""
