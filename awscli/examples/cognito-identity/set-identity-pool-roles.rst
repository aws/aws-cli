**To set identity pool roles**

The following ``set-identity-pool-roles`` example sets an identity pool role. ::

    aws cognito-identity set-identity-pool-roles \
        --identity-pool-id "us-west-2:11111111-1111-1111-1111-111111111111" \
        --roles authenticated="arn:aws:iam::111111111111:role/Cognito_MyIdentityPoolAuth_Role"

This command produces no output.

For more information, see `IAM roles <https://docs.aws.amazon.com/cognito/latest/developerguide/iam-roles.html>`__ in the *Amazon Cognito Developer Guide*.
