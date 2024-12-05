**To Cancel an export task**

The following ``cancel-export-task`` example cancels the export task with id ``a1b2c3d4-5678-90ab-cdef-example12345``. If the command succeeds, no output is returned. ::

    aws logs cancel-export-task \
        --task-id a1b2c3d4-5678-90ab-cdef-example12345

For more information, see `Exporting log data to Amazon S3 <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3Export.html>`__ in the *Amazon CloudWatch Logs User Guide*.