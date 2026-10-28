**To cancel a stack update that is in progress**

The following ``cancel-update-stack`` example cancels a stack update on the ``myteststack`` stack. This command produces no output. ::

    aws cloudformation cancel-update-stack \
        --stack-name myteststack
