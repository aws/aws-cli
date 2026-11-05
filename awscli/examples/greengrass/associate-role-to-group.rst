**To associate a role with a Greengrass group**

The following ``associate-role-to-group`` example associates the specified IAM role with a Greengrass group. The group role is used by local Lambda functions and connectors to access AWS services. For example, your group role might grant permissions required for CloudWatch Logs integration. ::

    aws greengrass associate-role-to-group \
        --group-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --role-arn arn:aws:iam::123456789012:role/GG-Group-Role

Output::

    {
        "AssociatedAt": "2019-09-10T20:03:30Z"
    }

For more information, see `Configure the group role <https://docs.aws.amazon.com/greengrass/v1/developerguide/config-iam-roles.html>`__ in the *AWS IoT Greengrass Developer Guide*.
