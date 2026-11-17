**To unsuspend multiple users**

The following ``batch-unsuspend-user`` example removes any previous suspension for the listed users on the specified Amazon Chime account. ::

    aws chime batch-unsuspend-user \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-id-list "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222" "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333" "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"

Output::

    {
        "UserErrors": []
    }

For more information, see `Managing user permissions and access <https://docs.aws.amazon.com/chime/latest/ag/manage-access.html>`__ in the *Amazon Chime Administration Guide*.
