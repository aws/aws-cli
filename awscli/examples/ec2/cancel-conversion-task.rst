**To cancel an active conversion of an instance or a volume**

The following ``cancel-conversion-task`` example cancels the upload associated with the task ID import-i-fh95npoc. If the command succeeds, no output is returned. ::

    aws ec2 cancel-conversion-task \
        --conversion-task-id import-i-fh95npoc
