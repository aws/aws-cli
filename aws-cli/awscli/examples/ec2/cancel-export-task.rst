**To cancel an active export task**

The following ``cancel-export-task`` example cancels an active export task with the task ID export-i-fgelt0i7. ::

    aws ec2 cancel-export-task \
        --export-task-id export-i-fgelt0i7

This command produces no output.

For more information, see `Export an EC2 instance as a VM using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport.html>`__ in the *VM Import/Export User Guide*.
