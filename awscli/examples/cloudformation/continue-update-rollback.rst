**To retry an update rollback**

The following ``continue-update-rollback`` example resumes a rollback operation from a previously failed stack update. ::

    aws cloudformation continue-update-rollback \
        --stack-name my-stack

This command produces no output.

For more information, see `Continue rolling back an update <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-continueupdaterollback.html>`__ in the *AWS CloudFormation User Guide*.
