**To create a network interface permission**

The following ``create-network-interface-permission`` example grants permission to account ``123456789012`` to attach network interface ``eni-1a2b3c4d`` to an instance. ::

    aws ec2 create-network-interface-permission \
        --network-interface-id eni-1a2b3c4d \
        --aws-account-id 123456789012 \
        --permission INSTANCE-ATTACH

Output::

    {
        "InterfacePermission": {
            "PermissionState": {
                "State": "GRANTED"
            },
            "NetworkInterfacePermissionId": "eni-perm-06fd19020ede149ea",
            "NetworkInterfaceId": "eni-1a2b3c4d",
            "Permission": "INSTANCE-ATTACH",
            "AwsAccountId": "123456789012"
        }
    }

For more information, see `Elastic network interfaces <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html>`__ in the *Amazon EC2 User Guide*.
