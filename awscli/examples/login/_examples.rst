**Example 1: To login with default parameters**

The following ``login`` example authenticates the CLI using your AWS Console session. A browser window opens automatically to complete the sign-in. ::

    aws login

Output::

    Attempting to open your default browser.
    If the browser does not open, open the following URL:

    https://signin.aws.amazon.com/...

    Updated profile default to use arn:aws:sts::123456789012:assumed-role/my-role/my-session-name credentials.

For more information, see `Login for AWS local development using console credentials <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html>`__ in the *AWS CLI User Guide*.

**Example 2: To login from a remote host**

The following ``login`` example uses the ``--remote`` option to authenticate from a host where a browser is not available, such as over SSH. You visit the provided URL on another device and paste the authorization code back into the CLI. ::

    aws login --remote

Output::

    Browser will not be automatically opened.
    Please visit the following URL:

    https://signin.aws.amazon.com/...

    Enter the authorization code displayed in your browser: XXXX

    Updated profile default to use arn:aws:sts::123456789012:assumed-role/my-role/my-session-name credentials.

For more information, see `Login for AWS local development using console credentials <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html>`__ in the *AWS CLI User Guide*.
