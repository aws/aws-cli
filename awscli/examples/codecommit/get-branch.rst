**To get information about a branch**

The following ``get-branch`` example gets information about a branch in an AWS CodeCommit repository. ::

    aws codecommit get-branch \
        --repository-name MyDemoRepo \
        --branch-name MyNewBranch

Output::

    {
        "branch": {
            "commitId": "317f8570EXAMPLE",
            "branchName": "MyNewBranch"
        }
    }

For more information, see `View branch details in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-view-branch-details.html#how-to-view-branch-details-cli-details>`__ in the *AWS CodeCommit User Guide*.
