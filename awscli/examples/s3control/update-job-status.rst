**To update the status of an Amazon S3 batch operations job**

The following ``update-job-status`` example cancels the specified job which is awaiting approval. ::

    aws s3control update-job-status \
        --account-id 123456789012 \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --requested-job-status Cancelled

Output::

    {
        "Status": "Cancelled",
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

The following ``update-job-status`` example confirms and runs the specified which is awaiting approval. ::

    aws s3control update-job-status \
        --account-id 123456789012 \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --requested-job-status Ready

Output::

    {
        "Status": "Ready",
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

The following ``update-job-status`` example cancels the specified job which is running. ::

    aws s3control update-job-status \
        --account-id 123456789012 \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --requested-job-status Cancelled

Output::

    {
        "Status": "Cancelling",
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Tracking job status and completion reports <https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-job-status.html>`__ in the *Amazon S3 User Guide*.
