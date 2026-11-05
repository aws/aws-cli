**To confirm sign-up**

The following ``confirm-sign-up`` example confirms sign-up for username diego@example.com. ::

    aws cognito-idp confirm-sign-up \
        --client-id 3n4b5urk1ft4fl3mg5e62d9ado \
        --username diego@example.com \
        --confirmation-code CONF_CODE

Output::

    {
        "Session": "AYABeEXAMPLEhLPy6WfPnN0bJ3VYeUg7Ryh2mB1xOCy2CFvpZx5jSEXAMPLE"
    }

For more information, see `Signing up and confirming user accounts <https://docs.aws.amazon.com/cognito/latest/developerguide/signing-up-users-in-your-app.html>`__ in the *Amazon Cognito Developer Guide*.
