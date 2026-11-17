**To create multiple associations**

The following ``create-association-batch`` example associates a configuration document with multiple instances. The output returns a list of successful and failed operations, if applicable. ::

    aws ssm create-association-batch \
        --entries "Name=AWS-UpdateSSMAgent,InstanceId=i-1234567890abcdef0" "Name=AWS-UpdateSSMAgent,InstanceId=i-9876543210abcdef0"

Output::

    {
        "Successful": [
            {
                "Name": "AWS-UpdateSSMAgent",
                "InstanceId": "i-1234567890abcdef0",
                "AssociationVersion": "1",
                "Date": 1550504725.007,
                "LastUpdateAssociationDate": 1550504725.007,
                "Status": {
                    "Date": 1550504725.007,
                    "Name": "Associated",
                    "Message": "Associated with AWS-UpdateSSMAgent"
                },
                "Overview": {
                    "Status": "Pending",
                    "DetailedStatus": "Creating"
                },
                "DocumentVersion": "$DEFAULT",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-1234567890abcdef0"
                        ]
                    }
                ]
            },
            {
                "Name": "AWS-UpdateSSMAgent",
                "InstanceId": "i-9876543210abcdef0",
                "AssociationVersion": "1",
                "Date": 1550504725.057,
                "LastUpdateAssociationDate": 1550504725.057,
                "Status": {
                    "Date": 1550504725.057,
                    "Name": "Associated",
                    "Message": "Associated with AWS-UpdateSSMAgent"
                },
                "Overview": {
                    "Status": "Pending",
                    "DetailedStatus": "Creating"
                },
                "DocumentVersion": "$DEFAULT",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-9876543210abcdef0"
                        ]
                    }
                ]
            }
        ],
        "Failed": []
    }

For more information, see `Creating associations <https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-associations-creating.html>`__ in the *AWS Systems Manager User Guide*.
