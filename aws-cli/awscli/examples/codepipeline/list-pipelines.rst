**To view a list of pipelines**

The following ``list-pipelines`` example lists all AWS CodePipeline pipelines associated with the user's AWS account. ::

    aws codepipeline list-pipelines

Output::

    {
        "pipelines": [
            {
                "updated": 1439504274.641,
                "version": 1,
                "name": "MyFirstPipeline",
                "created": 1439504274.641
            },
            {
                "updated": 1436461837.992,
                "version": 2,
                "name": "MySecondPipeline",
                "created": 1436460801.381
            }
        ]
    }

For more information, see `View pipeline details and history (CLI) <https://docs.aws.amazon.com/codepipeline/latest/userguide/pipelines-view-cli.html>`__ in the *AWS CodePipeline User Guide*.
