**To pause running until a conversion task is completed**

The following ``wait conversion-task-completed`` example pauses and continues only after it can confirm that the specified conversion task is completed. ::

    aws ec2 wait conversion-task-completed \
        --conversion-task-ids import-i-fh95npoc

This command produces no output.

For more information, see `Import a VM as an EC2 instance using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-instance-import.html>`__ in the *VM Import/Export User Guide*.
