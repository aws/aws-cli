**To modify an instance profile**

The following ``modify-instance-profile`` example updates the description and network type of an instance profile. ::

    aws dms modify-instance-profile \
        --instance-profile-identifier arn:aws:dms:us-east-1:123456789012:instance-profile:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --description "Updated instance profile description" \
        --network-type DUAL

Output::

    {
        "InstanceProfile": {
            "InstanceProfileArn": "arn:aws:dms:us-east-1:123456789012:instance-profile:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "KmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "PubliclyAccessible": false,
            "NetworkType": "DUAL",
            "InstanceProfileName": "example-instance-profile",
            "Description": "Updated instance profile description",
            "InstanceProfileCreationTime": "2026-01-09T12:30:00.000000+00:00",
            "SubnetGroupIdentifier": "example-replication-subnet-group",
            "VpcSecurityGroups": [
                "sg-0123456789abcdef0"
            ]
        }
    }

For more information, see `Working with instance profiles <https://docs.aws.amazon.com/dms/latest/userguide/instance-profiles.html>`__ in the *AWS Database Migration Service User Guide*.
