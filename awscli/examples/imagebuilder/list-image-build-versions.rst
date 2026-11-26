**To list the build versions of an image**

The following ``list-image-build-versions`` example lists the build versions that exist for version 1.0.0 of the specified image, with the output AMI that the build produced. ::

    aws imagebuilder list-image-build-versions \
        --image-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
                "name": "my-example-recipe",
                "type": "AMI",
                "version": "1.0.0/1",
                "platform": "Linux",
                "osVersion": "Amazon Linux 2023",
                "state": {
                    "status": "AVAILABLE"
                },
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:12:18.677Z",
                "outputResources": {
                    "amis": [
                        {
                            "region": "us-west-2",
                            "image": "ami-1234567890abcdef0",
                            "name": "my-example-recipe 2026-09-09T19-19-08.103311Z",
                            "accountId": "123456789012"
                        }
                    ]
                },
                "tags": {},
                "buildType": "USER_INITIATED"
            }
        ]
    }

For more information, see `List images and build versions <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-details-list.html>`__ in the *EC2 Image Builder User Guide*.
