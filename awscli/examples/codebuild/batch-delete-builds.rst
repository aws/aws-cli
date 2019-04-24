**Delete builds in AWS CodeBuild.**

The following ``batch-delete-builds`` example attempts to delete builds in CodeBuild with the following two IDs:
``my-demo-build-project:f8b888d2-5e1e-4032-8645-b115195648EX`` 
``my-other-demo-build-project:a18bc6ee-e499-4887-b36a-8c90349c7eEX`` ::

    aws codebuild batch-delete-builds --ids my-demo-build-project:f8b888d2-5e1e-4032-8645-b115195648EX my-other-demo-build-project:a18bc6ee-e499-4887-b36a-8c90349c7eEX

Output::

    {
        "buildsNotDeleted": [
            {
                "id": "arn:aws:codebuild:us-west-2:123456789012:build/my-demo-build-project:f8b888d2-5e1e-4032-8645-b115195648EX", 
                "statusCode": "BUILD_IN_PROGRESS"
            }
        ], 
        "buildsDeleted": [
            "arn:aws:codebuild:us-west-2:123456789012:build/my-other-demo-build-project:a18bc6ee-e499-4887-b36a-8c90349c7eEX"
        ]
    }

For more information, see `Delete Builds (AWS CLI`_ in the *AWS CodeBuild User Guide*

.. _`Delete Builds (AWS CLI`: https://docs.aws.amazon.com/codebuild/latest/userguide/delete-builds.html#delete-builds-cli
