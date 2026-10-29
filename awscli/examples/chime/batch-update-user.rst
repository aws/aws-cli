**To update multiple users in a single command**

The following ``batch-update-user`` example updates the ``LicenseType`` for each of the listed users in the specified Amazon Chime account. ::

    aws chime batch-update-user \
        --account-id a1b2c3d4-5678-90ab-cdef-11111EXAMPLE \
        --update-user-request-items "UserId=a1b2c3d4-5678-90ab-cdef-22222EXAMPLE,LicenseType=Basic" "UserId=a1b2c3d4-5678-90ab-cdef-33333EXAMPLE,LicenseType=Basic"

Output::

    {
        "UserErrors": []
    }

For more information, see `Managing user permissions and access <https://docs.aws.amazon.com/chime/latest/ag/manage-access.html>`__ in the *Amazon Chime Administration Guide*.
