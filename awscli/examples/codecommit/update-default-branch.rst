**To change the default branch for a repository**

The following ``update-default-branch`` example changes the default branch for an AWS CodeCommit repository. ::

    aws codecommit update-default-branch \
        --repository-name MyDemoRepo \
        --default-branch-name MyNewBranch

This command produces no output.
