**To update user details**

The following ``update-user`` example updates the specified details for the specified user. ::

    aws chime update-user \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --license-type "Basic"

Output::

    {
        "User": {
            "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        }
    }

For more information, see `Managing user permissions and access <https://docs.aws.amazon.com/chime/latest/ag/manage-access.html>`__ in the *Amazon Chime Administration Guide*.
