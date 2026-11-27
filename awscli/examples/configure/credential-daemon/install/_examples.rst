**Example 1: To install the credential daemon (Linux)**

The following ``credential-daemon install`` example downloads
aws-credential-daemon from its GitHub releases, checks its signature, and
installs it as a system service for every user on the machine. Run it with
``sudo``. Once the service answers, it links ``~/.aws/credential-daemon.sock``
to aws-credential-daemon's socket for root and, as that user, for the user who
ran ``sudo``. Other users on the machine run ``aws configure credential-daemon
link``. The output names each link it created and the socket it points to,
shown here as ``<socket>``. ::

    sudo aws configure credential-daemon install

Output::

    Downloading aws-credential-daemon from github.com/aws/credential-daemon...
    Installed aws-credential-daemon as a system service.
    Linked /root/.aws/credential-daemon.sock to <socket>.
    Linked /home/alice/.aws/credential-daemon.sock to <socket>.
    Your next sign-in will ask whether to store its session here.

Without root, the command downloads and changes nothing. It prints the
``sudo`` command to run and exits with 253.

Behind a proxy, keep its settings when you run ``sudo``, and pass
``--ca-bundle`` with the proxy's CA file if it inspects TLS. The command always
checks TLS, so it refuses ``--no-verify-ssl``. ::

    sudo --preserve-env=HTTPS_PROXY,https_proxy,NO_PROXY,no_proxy,AWS_CA_BUNDLE aws configure credential-daemon install

If aws-credential-daemon's installer fails, such as on a machine it can't run
on, the command shows the installer's error, creates no link, and exits with
253. If the installed service doesn't answer within 30 seconds, the command
says where to see why, creates no link, and exits with 253. Fix what it shows,
then run the command again.

**Example 2: To install the credential daemon (macOS)**

The following ``credential-daemon install`` example installs
aws-credential-daemon on macOS for the current user only, then links
``~/.aws/credential-daemon.sock`` to its socket, shown here as ``<socket>``.
Run it without ``sudo``. ::

    aws configure credential-daemon install

Output::

    Downloading aws-credential-daemon from github.com/aws/credential-daemon...
    Installed aws-credential-daemon for this user.
    Linked /Users/alice/.aws/credential-daemon.sock to <socket>.
    Your next sign-in will ask whether to store its session here.

For more information, see `Sealing credentials with AWS Credential Daemon <https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-credsd.html>`__ in the *AWS CLI User Guide*.
