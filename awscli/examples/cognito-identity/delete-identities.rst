**To delete identity pool**

The following ``delete-identities`` example deletes the specified identity. ::

    aws cognito-identity delete-identities \
        --identity-ids-to-delete "us-west-2:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "UnprocessedIdentityIds": []
    }

For more information, see `Amazon Cognito identity pools <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-identity.html>`__ in the *Amazon Cognito Developer Guide*.
