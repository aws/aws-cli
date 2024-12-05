**To Create an export task **

The following ``create-export-task`` example creates an export task to export data from a log group named ``demo-log-group`` to an Amazon S3 bucket named ``my-exported-logs``. ::

    aws logs create-export-task \
        --log-group-name demo-log-group \
        --from 1715918400 \
        --to 1715920200 \
        --destination my-exported-logs

Output::

    {
        "taskId": "a1b2c3d4-5678-90ab-cdef-example11111"
    }

For more information, see `Exporting log data to Amazon S3 <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3Export.html>`__ in the *Amazon CloudWatch Logs User Guide*.