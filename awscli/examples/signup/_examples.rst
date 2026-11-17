**Example 1: To create an AWS account and sign in to it**

The following ``signup`` example opens AWS account creation in your browser. When you finish creating the account, the CLI receives credentials for it and sets the profile's region to the account's home region. ::

    aws signup

Output::

    Attempting to open your default browser.
    If the browser does not open, open the following URL:

    https://us-east-1.signin.aws.amazon.com/...

    Set region to us-east-2, the home region for this account.

    Updated profile default to use arn:aws:sts::123456789012:assumed-role/my-role/my-session-name credentials.

For more information, see `Login for AWS local development using console credentials <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html>`__ in the *AWS CLI User Guide*.
