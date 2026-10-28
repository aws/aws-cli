**To delete a branch**

The following ``delete-branch`` example deletes a branch in an AWS CodeCommit repository. ::

    aws codecommit delete-branch \
        --repository-name MyDemoRepo \
        --branch-name MyNewBranch

Output::

    {
        "branch": {
            "commitId": "317f8570EXAMPLE",
            "branchName": "MyNewBranch"
        }
    }