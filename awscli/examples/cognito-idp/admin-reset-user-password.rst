**To reset a user password**

The following ``admin-reset-user-password`` example resets the password for diego@example.com. This command produces no output. ::

    aws cognito-idp admin-reset-user-password \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com
