**To add a file to a repository**

The following ``put-file`` example adds a file named 'ExampleSolution.py' to a repository named 'MyDemoRepo' to a branch named 'feature-randomizationfeature' whose most recent commit has an ID of '4c925148EXAMPLE'. ::

    aws codecommit put-file \
        --repository-name MyDemoRepo \
        --branch-name feature-randomizationfeature \
        --file-content fileb://MyDirectory/ExampleSolution.py \
        --file-path /solutions/ExampleSolution.py \
        --parent-commit-id 4c925148EXAMPLE \
        --name "Maria Garcia" \
        --email "maria_garcia@example.com" \
        --commit-message "I added a third randomization routine."

Output::

    {
        "blobId": "2eb4af3bEXAMPLE",
        "commitId": "317f8570EXAMPLE",
        "treeId": "347a3408EXAMPLE"
    }

For more information, see `Create or add a file to an AWS CodeCommit repository <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-create-file.html>`__ in the *AWS CodeCommit User Guide*.
