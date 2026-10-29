**To get a list of AWS CodeBuild builds IDs.**

The following ``list-builds`` example gets a list of CodeBuild IDs sorted in ascending order. ::

    aws codebuild list-builds \
        --sort-order ASCENDING

The output includes a ``nextToken`` value which indicates that there is more output available.

Output::

    {
        "nextToken": "4AEA6u7J...The full token has been omitted for brevity...MzY2OA==",
        "ids": [
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
        ]
    }

Run this command again and provide the ``nextToken`` value in the previous response as a parameter to get the next part of the output. Repeat until you don't receive a ``nextToken`` value in the response. ::

    aws codebuild list-builds \
        --sort-order ASCENDING \
        --next-token 4AEA6u7J...The full token has been omitted for brevity...MzY2OA==

Output::

    {
        "ids": [       
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
            "codebuild-demo-project:a1b2c3d4-5678-90ab-cdef-EXAMPLE66666"
        ]
    }

For more information, see `View a list of build IDs in AWS CodeBuild <https://docs.aws.amazon.com/codebuild/latest/userguide/view-build-list.html>`__ in the *AWS CodeBuild User Guide*.

