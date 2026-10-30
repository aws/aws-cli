**To change a password**

The following ``change-password`` example changes a password. ::

    aws cognito-idp change-password \
        --previous-password OldPassword \
        --proposed-password NewPassword \
        --access-token ACCESS_TOKEN

This command produces no output.
