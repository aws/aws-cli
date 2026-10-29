**To disassociate the role from a Greengrass group**

The following ``disassociate-role-from-group`` example disassociates the IAM role from the specified Greengrass group. ::

    aws greengrass disassociate-role-from-group \
        --group-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "DisassociatedAt": "2019-09-10T20:05:49Z"
    }

For more information, see `Configure the group role <https://docs.aws.amazon.com/greengrass/v1/developerguide/config-iam-roles.html>`__ in the *AWS IoT Greengrass Developer Guide*.
