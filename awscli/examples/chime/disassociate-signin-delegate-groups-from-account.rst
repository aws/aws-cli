**To disassociate sign-in delegate groups**

The following ``disassociate-signin-delegate-groups-from-account`` example disassociates the specified sign-in delegate group from the specified Amazon Chime account. ::

    aws chime disassociate-signin-delegate-groups-from-account \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --group-names "my_users"

This command produces no output.

For more information, see `Managing User Access and Permissions <https://docs.aws.amazon.com/chime/latest/ag/manage-access.html>`__ in the *Amazon Chime Administration Guide*.
