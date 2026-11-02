**To delete builds in AWS CodeBuild.**

The following ``batch-delete-builds`` example deletes builds in CodeBuild with the specified IDs. ::

    aws codebuild batch-delete-builds \
        --ids my-build-project-one:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 my-build-project-two:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "buildsNotDeleted": [
            {
                "id": "arn:aws:codebuild:us-west-2:123456789012:build/my-build-project-one:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111", 
                "statusCode": "BUILD_IN_PROGRESS"
            }
        ], 
        "buildsDeleted": [
            "arn:aws:codebuild:us-west-2:123456789012:build/my-build-project-two:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        ]
    }

For more information, see `Delete builds in AWS CodeBuild <https://docs.aws.amazon.com/codebuild/latest/userguide/delete-builds.html>`__ in the *AWS CodeBuild User Guide*.

