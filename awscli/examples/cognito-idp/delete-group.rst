**To delete a group**

The following ``delete-group`` example deletes a group. ::

    aws cognito-idp delete-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --group-name MyGroupName

This command produces no output.

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
