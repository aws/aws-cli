**To check the status of an image build**

The following ``get-image`` example retrieves an image build version to check its status while the build is running. The output is shortened to show a subset of the fields that Image Builder returns. ::

    aws imagebuilder get-image \
        --image-build-version-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "image": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-recipe/1.0.0/1",
            "type": "AMI",
            "name": "my-example-recipe",
            "version": "1.0.0/1",
            "platform": "Linux",
            "enhancedImageMetadataEnabled": true,
            "state": {
                "status": "BUILDING"
            },
            "sourcePipelineArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline",
            "dateCreated": "2026-09-03T05:44:21.121Z",
            "tags": {}
        }
    }

For more information, see `View image resource details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/view-image-details.html>`__ in the *EC2 Image Builder User Guide*.
