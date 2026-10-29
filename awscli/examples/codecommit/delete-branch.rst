**To delete a branch**

The following ``delete-branch`` example deletes a branch in an AWS CodeCommit repository. ::

    aws codecommit delete-branch \
        --repository-name MyDemoRepo \
        --branch-name MyNewBranch

Output::

    {
        "deletedBranch": {
            "commitId": "317f8570EXAMPLE",
            "branchName": "MyNewBranch"
        }
    }

For more information, see `Delete a branch in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-delete-branch.html#how-to-delete-branch-cli>`__ in the *AWS CodeCommit User Guide*.
