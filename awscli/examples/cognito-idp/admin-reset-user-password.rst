**To reset a user password**

The following ``admin-reset-user-password`` example resets the password for diego@example.com. ::

    aws cognito-idp admin-reset-user-password \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com

This command produces no output.

For more information, see `Passwords, account recovery, and password policies <https://docs.aws.amazon.com/cognito/latest/developerguide/managing-users-passwords.html>`__ in the *Amazon Cognito Developer Guide*.
