**To create a branch**

The following ``create-branch`` example creates a branch in an AWS CodeCommit repository. ::

    aws codecommit create-branch \
        --repository-name MyDemoRepo \
        --branch-name MyNewBranch \
        --commit-id 317f8570EXAMPLE

This command produces no output.
