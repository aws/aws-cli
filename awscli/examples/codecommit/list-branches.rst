**To view a list of branch names**

The following ``list-branches`` example lists all branch names in an AWS CodeCommit repository. ::

    aws codecommit list-branches \
        --repository-name MyDemoRepo

Output::

    {
        "branches": [
            "MyNewBranch",
            "main"
        ]
    }

For more information, see `View branch details in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-branch-details.html>`__ in the *AWS CodeCommit User Guide*.
