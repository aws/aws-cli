**To associate a RAM managed permission with a resource share**

The following ``associate-resource-share-permission`` example replaces the existing managed permission for the relevant resource type with the specified managed permission. Access to all resources of the relevant resource type is governed by the new permission. ::

    aws ram associate-resource-share-permission \
        --permission-arn arn:aws:ram::aws:permission/AWSRAMPermissionGlueDatabaseReadWrite \
        --replace \
        --resource-share-arn arn:aws:ram:us-west-2:123456789012:resource-share/27d09b4b-5e12-41d1-a4f2-19dedEXAMPLE

Output::

    {
        "returnValue": true
    }

For more information, see `Managing permissions in AWS RAM <https://docs.aws.amazon.com/ram/latest/userguide/security-ram-permissions.html>`__ in the *AWS RAM User Guide*.
