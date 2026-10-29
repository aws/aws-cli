**To list image pipeline pipeline images**

The following ``list-image-pipeline-images`` example lists all images that were created by a specific image pipeline. ::

    aws imagebuilder list-image-pipeline-images \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/mywindows2016pipeline

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imageSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image/mybasicrecipe/2019.12.03/1",
                "name": "MyBasicRecipe",
                "version": "2019.12.03/1",
                "platform": "Windows",
                "state": {
                    "status": "AVAILABLE"
                },
                "owner": "123456789012",
                "dateCreated": "2020-02-19T19:04:01.253Z",
                "outputResources": {
                    "amis": [
                        {
                            "region": "us-west-2",
                            "image": "ami-a1b2c3d4567890ab",
                            "name": "MyBasicRecipe 2020-02-19T19-04-01.253Z",
                            "description": "Builds Windows 2016 Images"
                        }
                    ]
                },
                "tags": {
                    "KeyName": "KeyValue"
                }
            }
        ]
    }

For more information, see `Manage custom image creation in Image Builder through a repeatable pipeline process <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html>`__ in the *EC2 Image Builder Users Guide*.
