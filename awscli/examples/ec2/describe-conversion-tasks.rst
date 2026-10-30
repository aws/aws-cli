**To view the status of a conversion task**

The following ``describe-conversion-tasks`` example returns the status of a conversion task with the ID import-i-ffvko9js. ::

    aws ec2 describe-conversion-tasks \
        --conversion-task-ids import-i-ffvko9js

Output::

    {
        "ConversionTasks": [
            {
                "ConversionTaskId": "import-i-ffvko9js",
                "ImportInstance": {
                    "InstanceId": "i-1234567890abcdef0",
                    "Volumes": [
                        {
                            "Volume": {
                                "Id": "vol-049df61146c4d7901",
                                "Size": 16
                            },
                            "Status": "completed",
                            "Image": {
                                "Size": 1300687360,
                                "ImportManifestUrl": "https://s3.amazonaws.com/myimportbucket/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/RHEL5.vmdkmanifest.xml?AWSAccessKeyId=AKIAIOSFODNN7EXAMPLE&Expires=140EXAMPLE&Signature=XYNhznHNgCqsjDxL9wRL%2FJvEXAMPLE",
                                "Format": "VMDK"
                            },
                            "BytesConverted": 1300682960,
                            "AvailabilityZone": "us-west-2d"
                        }
                    ]
                },
                "ExpirationTime": "2014-05-14T22:06:23Z",
                "State": "completed"
            }
        ]
    }

For more information, see `Import a VM as an EC2 instance using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-instance-import.html>`__ in the *VM Import/Export User Guide*.
