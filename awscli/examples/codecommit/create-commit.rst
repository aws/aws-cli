**To create a commit**

The following ``create-commit`` example demonstrates how to create an initial commit for a repository that adds a ``readme.md`` file to a repository named ``MyDemoRepo`` in the ``main`` branch. The ``fileContent`` value is the base64-encoded text ``Welcome to our team repository.``. ::

    aws codecommit create-commit \
        --repository-name MyDemoRepo \
        --branch-name main \
        --put-files "filePath=readme.md,fileContent=V2VsY29tZSB0byBvdXIgdGVhbSByZXBvc2l0b3J5Lg=="

Output::

    {
        "filesAdded": [
            {
                "blobId": "5e1c309d-EXAMPLE",
                "absolutePath": "readme.md",
                "fileMode": "NORMAL"
            }
        ],
        "commitId": "4df8b524-EXAMPLE",
        "treeId": "55b57003-EXAMPLE",
        "filesDeleted": [],
        "filesUpdated": []
    }

For more information, see `Create a Commit in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-create-commit.html#how-to-create-commit-cli>`__ in the *AWS CodeCommit User Guide*.