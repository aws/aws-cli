**To list the images that an image pipeline created**

The following ``list-image-pipeline-images`` example lists the images that the specified pipeline created, including a build that is still in progress. ::

    aws imagebuilder list-image-pipeline-images \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline

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
                "state": {
                    "status": "BUILDING"
                },
                "owner": "123456789012",
                "dateCreated": "2026-09-09T19:39:20.458Z",
                "outputResources": {
                    "amis": []
                },
                "tags": {},
                "buildType": "USER_INITIATED"
            }
        ]
    }

For more information, see `List and view pipeline details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/pipeline-details.html>`__ in the *EC2 Image Builder User Guide*.
