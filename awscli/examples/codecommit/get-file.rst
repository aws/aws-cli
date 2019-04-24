**To get the base-64 encoded contents of a file in an AWS CodeCommit repository**

The following ``get-file`` example demonstrates how to get the base-64 encoded contents of a file named ``README.md`` from a branch named ``master`` in a repository named ``MyDemoRepo``. ::

    aws codecommit get-file --repository-name MyDemoRepo --commit-specifier master --file-path README.md

Output::

    {
        "blobId":"559b44fEXAMPLE",
        "commitId":"c5709475EXAMPLE",
        "fileContent":"IyBQaHVzEXAMPLE",
        "filePath":"README.md",
        "fileMode":"NORMAL",
        "fileSize":1563
    }

For more information, see `GetFile`_ in the *AWS CodeCommit API Reference* guide.

.. _`GetFile`: https://docs.aws.amazon.com/codecommit/latest/APIReference/API_GetFile.html
