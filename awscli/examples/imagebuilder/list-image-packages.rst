**To list the packages in an image build version**

The following ``list-image-packages`` example lists the operating system packages that Image Builder detected in the specified image build version. ::

    aws imagebuilder list-image-packages \
        --image-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imagePackageList": [
            {
                "packageName": "passwd",
                "packageVersion": "0.80"
            },
            {
                "packageName": "dracut-config-ec2",
                "packageVersion": "3.1"
            },
            {
                "packageName": "libsolv",
                "packageVersion": "0.7.22"
            },
            {
                "packageName": "libxcrypt",
                "packageVersion": "4.4.33"
            },
            {
                "packageName": "python3-policycoreutils",
                "packageVersion": "3.4"
            }
        ]
    }

For more information, see `View image resource details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/view-image-details.html>`__ in the *EC2 Image Builder User Guide*.
