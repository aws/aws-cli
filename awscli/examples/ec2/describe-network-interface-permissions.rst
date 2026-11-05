**To describe your network interface permissions**

The following ``describe-network-interface-permissions`` example describes all of your network interface permissions. ::

    aws ec2 describe-network-interface-permissions

Output::

    {
        "NetworkInterfacePermissions": [
            {
                "PermissionState": {
                    "State": "GRANTED"
                },
                "NetworkInterfacePermissionId": "eni-perm-06fd19020ede149ea",
                "NetworkInterfaceId": "eni-b909511a",
                "Permission": "INSTANCE-ATTACH",
                "AwsAccountId": "123456789012"
            }
        ]
    }

For more information, see `Elastic network interfaces <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html>`__ in the *Amazon EC2 User Guide*.
