**To sign up a user**

The following ``sign-up`` example signs up jane@example.com. ::

    aws cognito-idp sign-up \
        --client-id 3n4b5urk1ft4fl3mg5e62d9ado \
        --username jane@example.com \
        --password PASSWORD \
        --user-attributes Name="email",Value="jane@example.com" Name="name",Value="Jane"

Output::

    {
        "UserConfirmed": false,
        "UserSub": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Signing up and confirming user accounts <https://docs.aws.amazon.com/cognito/latest/developerguide/signing-up-users-in-your-app.html>`__ in the *Amazon Cognito Developer Guide*.
