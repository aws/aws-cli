**Gets a list of AWS CodeBuild build project names.**

The following ``list-projects`` example gets a list of CodeBuild build projects sorted by name in ascending order. ::

    aws codebuild list-projects --sort-by NAME --sort-order ASCENDING 

Output::

    {
        "nextToken": "Ci33ACF6...The full token has been omitted for brevity...U+AkMx8=",
        "projects": [
            "codebuild-demo-project",
            "codebuild-demo-project2",
            ... The full list of build project names has been omitted for brevity ...
            "codebuild-demo-project99"
        ]
    }

If you run this command again::

    aws codebuild list-projects  --sort-by NAME --sort-order ASCENDING --next-token Ci33ACF6...The full token has been omitted for brevity...U+AkMx8=

Output::

    {
        "projects": [
            "codebuild-demo-project100",
            "codebuild-demo-project101",
            ... The full list of build project names has been omitted for brevity ...
            "codebuild-demo-project122"
        ]
    }

For more information, see `View a List of Build Project Names (AWS CLI)`_ in the *AWS CodeBuild User Guide*

.. _`View a List of Build Project Names (AWS CLI)`: https://docs.aws.amazon.com/codebuild/latest/userguide/view-project-list.html#view-project-list-cli
