**To delete identity pool**

The following ``delete-identities`` example deletes the specified identity. ::

    aws cognito-identity delete-identities \
        --identity-ids-to-delete "us-west-2:11111111-1111-1111-1111-111111111111"

Output::

    {
        "UnprocessedIdentityIds": []
    }
