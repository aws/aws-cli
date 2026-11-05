**To change a password**

The following ``change-password`` example changes a password. ::

    aws cognito-idp change-password \
        --previous-password OldPassword \
        --proposed-password NewPassword \
        --access-token ACCESS_TOKEN

This command produces no output.

For more information, see `Passwords, account recovery, and password policies <https://docs.aws.amazon.com/cognito/latest/developerguide/managing-users-passwords.html>`__ in the *Amazon Cognito Developer Guide*.
