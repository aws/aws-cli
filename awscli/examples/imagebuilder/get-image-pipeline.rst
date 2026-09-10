**To get the details of an image pipeline**

The following ``get-image-pipeline`` example retrieves an image pipeline that builds a new image every Sunday, including the image tests configuration and schedule start condition defaults that Image Builder applied at creation. ::

    aws imagebuilder get-image-pipeline \
        --image-pipeline-arn arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imagePipeline": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline",
            "name": "my-example-pipeline",
            "description": "Builds an Amazon Linux 2023 image every Sunday",
            "platform": "Linux",
            "enhancedImageMetadataEnabled": true,
            "imageRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0",
            "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure",
            "imageTestsConfiguration": {
                "imageTestsEnabled": true,
                "timeoutMinutes": 720
            },
            "schedule": {
                "scheduleExpression": "cron(0 0 ? * SUN *)",
                "pipelineExecutionStartCondition": "EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE"
            },
            "status": "ENABLED",
            "dateCreated": "2026-09-09T19:38:26.574Z",
            "dateUpdated": "2026-09-09T19:38:26.574Z",
            "tags": {}
        }
    }

For more information, see `List and view pipeline details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/pipeline-details.html>`__ in the *EC2 Image Builder User Guide*.
