**To list images that you own**

The following ``list-images`` example lists the image versions that your account owns. With ``--no-by-name``, each version of an image appears as its own entry. ::

    aws imagebuilder list-images \
        --owner Self \
        --no-by-name

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageVersionList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0",
                "name": "my-example-recipe",
                "type": "AMI",
                "version": "1.0.0",
                "platform": "Linux",
                "osVersion": "Amazon Linux 2023",
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:12:18.677Z",
                "buildType": "USER_INITIATED"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-windows-image/1.0.0",
                "name": "my-example-windows-image",
                "type": "AMI",
                "version": "1.0.0",
                "platform": "Windows",
                "osVersion": "Microsoft Windows Server 2025",
                "owner": "123456789012",
                "dateCreated": "2026-03-10T19:57:27.323Z",
                "buildType": "USER_INITIATED"
            },
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-windows-image/1.0.1",
                "name": "my-example-windows-image",
                "type": "AMI",
                "version": "1.0.1",
                "platform": "Windows",
                "osVersion": "Microsoft Windows Server 2025",
                "owner": "123456789012",
                "dateCreated": "2026-03-10T20:32:31.795Z",
                "buildType": "USER_INITIATED"
            }
        ]
    }

For more information, see `List images and build versions <https://docs.aws.amazon.com/imagebuilder/latest/userguide/image-details-list.html>`__ in the *EC2 Image Builder User Guide*.
