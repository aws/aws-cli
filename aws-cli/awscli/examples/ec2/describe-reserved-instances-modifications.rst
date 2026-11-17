**To describe Reserved Instances modifications**

The following ``describe-reserved-instances-modifications`` example describes all the Reserved Instances modification requests that have been submitted for your account. ::

    aws ec2 describe-reserved-instances-modifications

Output::

    {
        "ReservedInstancesModifications": [
            {
                "Status": "fulfilled",
                "ModificationResults": [
                    {
                        "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                        "TargetConfiguration": {
                            "AvailabilityZone": "us-west-2b",
                            "InstanceType": "m1.large",
                            "InstanceCount": 3
                        }
                    },
                    {
                        "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                        "TargetConfiguration": {
                            "AvailabilityZone": "us-west-2d",
                            "InstanceType": "m1.xlarge",
                            "InstanceCount": 1
                        }
                    }
                ],
                "EffectiveDate": "2015-08-12T17:00:00.000Z",
                "CreateDate": "2015-08-12T17:52:52.630Z",
                "UpdateDate": "2015-08-12T18:08:06.698Z",
                "ClientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "ReservedInstancesModificationId": "rimod-d3ed4335-b1d3-4de6-ab31-0f13aaf46687",
                "ReservedInstancesIds": [
                    {
                        "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
                    }
                ]
            }
        ]
    }

For more information, see `Modify Reserved Instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-modifying.html>`__ in the *Amazon EC2 User Guide*.
