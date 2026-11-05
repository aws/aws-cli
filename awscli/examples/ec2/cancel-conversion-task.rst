**To cancel an active conversion of an instance or a volume**

The following ``cancel-conversion-task`` example cancels the upload associated with the task ID import-i-fh95npoc. ::

    aws ec2 cancel-conversion-task \
        --conversion-task-id import-i-fh95npoc

This command produces no output.

For more information, see `Import a VM as an EC2 instance using VM Import/Export <https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-instance-import.html>`__ in the *VM Import/Export User Guide*.
