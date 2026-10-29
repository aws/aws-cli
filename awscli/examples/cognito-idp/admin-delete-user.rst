**To delete a user**

The following ``admin-delete-user`` example deletes a user. ::

    aws cognito-idp admin-delete-user \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com

This command produces no output.

For more information, see `Managing and searching for user accounts <https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-manage-user-accounts.html>`__ in the *Amazon Cognito Developer Guide*.
