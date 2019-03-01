**To get identity pool roles**

This example sets an identity pool role.

Command::

  aws cognito-identity set-identity-pool-roles --identity-pool-id "us-west-2:11111111-1111-1111-1111-111111111111" authenticated="arn:aws:iam::111111111111:role/Cognito_MyIdentityPoolAuth_Role"
