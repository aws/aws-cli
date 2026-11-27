**Example 1: To link the credential daemon for your user**

The following ``credential-daemon link`` example links
``~/.aws/credential-daemon.sock``, where the AWS CLI and SDKs look for the
credential daemon, to aws-credential-daemon's own socket. Run it without
``sudo``, for example after another user installed aws-credential-daemon on a
Linux machine. It checks the socket first and sends it nothing. The output
names the link and the socket it points to, shown here as ``<socket>``. ::

    aws configure credential-daemon link

Output::

    Linked /home/alice/.aws/credential-daemon.sock to <socket>.

**Example 2: To remove the link**

The following ``credential-daemon link`` example removes the link, for
example after aws-credential-daemon was uninstalled. ::

    aws configure credential-daemon link \
        --remove

Output::

    Removed /home/alice/.aws/credential-daemon.sock.

For more information, see `Sealing credentials with AWS Credential Daemon <https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-credsd.html>`__ in the *AWS CLI User Guide*.
