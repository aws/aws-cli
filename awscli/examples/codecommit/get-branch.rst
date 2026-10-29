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
