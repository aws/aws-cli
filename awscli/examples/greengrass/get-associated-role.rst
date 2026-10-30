**To get the role associated with a Greengrass group**

The following ``get-associated-role`` example gets the IAM role that's associated with the specified Greengrass group. The group role is used by local Lambda functions and connectors to access AWS services. ::

    aws greengrass get-associated-role \
        --group-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "RoleArn": "arn:aws:iam::123456789012:role/GG-Group-Role",
        "AssociatedAt": "2019-09-10T20:03:30Z"
    }

For more information, see `Configure the group role <https://docs.aws.amazon.com/greengrass/v1/developerguide/config-iam-roles.html>`__ in the *AWS IoT Greengrass Developer Guide*.
