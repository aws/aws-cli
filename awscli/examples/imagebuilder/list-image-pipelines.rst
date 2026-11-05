**To list image pipelines filtered by name**

The following ``list-image-pipelines`` example lists the image pipelines in your account, using a filter to match a specific pipeline name. ::

    aws imagebuilder list-image-pipelines \
        --filters name=name,values=my-example-pipeline

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "imagePipelineList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:image-pipeline/my-example-pipeline",
                "name": "my-example-pipeline",
                "description": "Builds a new version of my image every Sunday",
                "platform": "Linux",
                "enhancedImageMetadataEnabled": true,
                "imageRecipeArn": "arn:aws:imagebuilder:us-west-2:123456789012:image-recipe/my-example-recipe/1.0.0",
                "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure",
                "imageTestsConfiguration": {
                    "imageTestsEnabled": true,
                    "timeoutMinutes": 720
                },
                "schedule": {
                    "scheduleExpression": "cron(0 9 ? * SUN *)",
                    "pipelineExecutionStartCondition": "EXPRESSION_MATCH_AND_DEPENDENCY_UPDATES_AVAILABLE"
                },
                "status": "ENABLED",
                "dateCreated": "2026-09-09T19:52:05.146Z",
                "dateUpdated": "2026-09-09T19:52:05.146Z",
                "tags": {}
            }
        ]
    }

For more information, see `List and view pipeline details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/pipeline-details.html>`__ in the *EC2 Image Builder User Guide*.
