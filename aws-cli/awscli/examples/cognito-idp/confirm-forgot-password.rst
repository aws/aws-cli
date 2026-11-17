**To confirm a forgotten password**

The following ``confirm-forgot-password`` example confirms a forgotten password for username diego@example.com. ::

    aws cognito-idp confirm-forgot-password \
        --client-id 3n4b5urk1ft4fl3mg5e62d9ado \
        --username diego@example.com \
        --password PASSWORD \
        --confirmation-code CONF_CODE

This command produces no output.

For more information, see `Passwords, account recovery, and password policies <https://docs.aws.amazon.com/cognito/latest/developerguide/managing-users-passwords.html>`__ in the *Amazon Cognito Developer Guide*.
