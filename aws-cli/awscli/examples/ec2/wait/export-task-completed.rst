**To pause running until an export task is completed**

The following ``wait export-task-completed`` example pauses and continues only after it can confirm that the specified export task is completed. ::

    aws ec2 wait export-task-completed \
        --export-task-ids export-i-fgelt0i7

This command produces no output.

For more information, see `Export an EC2 instance as a VM using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmexport.html>`__ in the *VM Import/Export User Guide*.
