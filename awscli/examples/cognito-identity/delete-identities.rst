**To delete an identity**

This example deletes an identity from an identity pool.

Command::

  aws cognito-identity delete-identities --identity-ids-to-delete "us-west-2:11111111-1111-1111-1111-111111111111"

Output::

  {
    "UnprocessedIdentityIds": []
  }
