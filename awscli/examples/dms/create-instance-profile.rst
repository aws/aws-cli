**To create an instance profile**

The following ``create-instance-profile`` example creates an instance profile. ::

    aws dms create-instance-profile \
        --instance-profile-name example-instance-profile \
        --description "Example instance profile for documentation" \
        --subnet-group-identifier example-replication-subnet-group \
        --vpc-security-groups "sg-0123456789abcdef0" \
        --kms-key-arn arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --network-type IPV4 \
        --no-publicly-accessible

Output::

    {
        "InstanceProfile": {
            "InstanceProfileArn": "arn:aws:dms:us-east-1:123456789012:instance-profile:EXAMPLEABCDEFGHIJKLMNOPQRS",
            "KmsKeyArn": "arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "PubliclyAccessible": false,
            "NetworkType": "IPV4",
            "InstanceProfileName": "example-instance-profile",
            "Description": "Example instance profile for documentation",
            "InstanceProfileCreationTime": "2026-01-09T12:30:00.000000+00:00",
            "SubnetGroupIdentifier": "example-replication-subnet-group",
            "VpcSecurityGroups": [
                "sg-0123456789abcdef0"
            ]
        }
    }

For more information, see `Working with instance profiles <https://docs.aws.amazon.com/dms/latest/userguide/instance-profiles.html>`__ in the *AWS Database Migration Service User Guide*.
