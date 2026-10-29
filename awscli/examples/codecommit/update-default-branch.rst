**To change the default branch for a repository**

The following ``update-default-branch`` example changes the default branch for an AWS CodeCommit repository. ::

    aws codecommit update-default-branch \
        --repository-name MyDemoRepo \
        --default-branch-name MyNewBranch

This command produces no output.

For more information, see `Change branch settings in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-change-branch.html>`__ in the *AWS CodeCommit User Guide*.
