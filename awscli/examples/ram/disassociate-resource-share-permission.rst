**To remove a RAM managed permission for a resource type from a resource share**

The following ``disassociate-resource-share-permission`` example removes the RAM managed permission for Glue databases from the specified resource share. ::

    aws ram disassociate-resource-share-permission \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --permission-arn arn:aws:ram::aws:permission/AWSRAMPermissionGlueDatabaseReadWrite

Output::

    {
        "returnValue": true
    }

For more information, see `Managing permissions in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/security-ram-permissions.html>`__ in the *AWS RAM User Guide*.
