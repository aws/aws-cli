**To create a branch**

The following ``create-branch`` example creates a branch in an AWS CodeCommit repository. ::

    aws codecommit create-branch \
        --repository-name MyDemoRepo \
        --branch-name MyNewBranch \
        --commit-id 317f8570EXAMPLE

This command produces no output.

For more information, see `Create a branch in AWS CodeCommit <https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-create-branch.html#how-to-create-branch-cli>`__ in the *AWS CodeCommit User Guide*.
