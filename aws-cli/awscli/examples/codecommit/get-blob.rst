**To view information about a Git blob object**

The following ``get-blob`` example retrieves information about a Git blob with the ID of '2eb4af3bEXAMPLE' in an AWS CodeCommit repository named 'MyDemoRepo'. ::

    aws codecommit get-blob \
        --repository-name MyDemoRepo \
        --blob-id 2eb4af3bEXAMPLE

Output::

    {
        "content": "QSBCaW5hcnkgTGFyToEXAMPLE="
    }

For more information, see `View commit details in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-commit-details.html#how-to-view-commit-details-cli-blob>`__ in the *AWS CodeCommit User Guide*.
