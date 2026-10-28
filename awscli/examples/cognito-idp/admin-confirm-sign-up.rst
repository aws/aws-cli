**To confirm user registration**

The following ``admin-confirm-sign-up`` example confirms user jane@example.com. This command produces no output. ::

    aws cognito-idp admin-confirm-sign-up \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username jane@example.com

