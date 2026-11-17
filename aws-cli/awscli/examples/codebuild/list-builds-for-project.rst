**To view a list of builds for an AWS CodeBuild build project.**

The following ``list-builds-for-project`` example lists the build IDs in descending order for the specified CodeBuild build project. ::

    aws codebuild list-builds-for-project \
        --project-name codebuild-demo-project \
        --sort-order DESCENDING

Output::

    {
        "ids": [
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE55555"
        ]
    }

For more information, see `View a list of build IDs for a build project in AWS CodeBuild <https://docs.aws.amazon.com/codebuild/latest/userguide/view-builds-for-project.html>`__ in the *AWS CodeBuild User Guide*.
