**Example 1: To uninstall the credential daemon (Linux)**

The following ``credential-daemon uninstall`` example runs
aws-credential-daemon's own uninstaller, then removes the files the install
added, root's ``~/.aws/credential-daemon.sock`` link to its socket, and the
link of the user who ran ``sudo``. Other users remove theirs with ``aws
configure credential-daemon link --remove``. It asks first, because profiles
that use the credential daemon stop working until they move back to files. A
profile with access keys there doesn't move: remove its ``credential_daemon``
and enter the keys again with ``aws configure``. Run it with ``sudo``. ::

    sudo aws configure credential-daemon uninstall

Output::

    Profiles that use the credential daemon stop working until they move back to files.
    To move them back before uninstalling, answer no and set credential_storage = file in each profile. Each profile moves at its next sign-in. A profile with access keys there doesn't move: remove its credential_daemon and enter the keys again with aws configure.
    This removes it for every user on this machine. Continue? [y/N] y
    Removed aws-credential-daemon. The credential daemon's saved sign-ins and keys stay on this machine, so reinstalling brings them back. Nothing else in ~/.aws was changed.
    Removed /root/.aws/credential-daemon.sock.
    Removed /home/alice/.aws/credential-daemon.sock.

Without root, the command changes nothing. It prints the ``sudo`` command to
run and exits with 253.

**Example 2: To uninstall without being asked**

The following ``credential-daemon uninstall`` example uses ``--yes`` to
uninstall without asking, such as in a script with no terminal to answer the
question. ::

    sudo aws configure credential-daemon uninstall \
        --yes

Output::

    Removed aws-credential-daemon. The credential daemon's saved sign-ins and keys stay on this machine, so reinstalling brings them back. Nothing else in ~/.aws was changed.
    Removed /root/.aws/credential-daemon.sock.
    Removed /home/alice/.aws/credential-daemon.sock.

For more information, see `Sealing credentials with AWS Credential Daemon <https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-credsd.html>`__ in the *AWS CLI User Guide*.
