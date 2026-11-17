**To remove a user from a group**

The following ``admin-remove-user-from-group`` example removes jane@example.com from SampleGroup. ::

    aws cognito-idp admin-remove-user-from-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username jane@example.com \
        --group-name SampleGroup

This command produces no output.

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
