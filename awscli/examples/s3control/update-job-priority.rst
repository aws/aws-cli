**To update the job priority of an Amazon S3 batch operations job**

The following ``update-job-priority`` example updates the specified job to a new priority. ::

    aws s3control update-job-priority \
        --account-id 123456789012 \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --priority 52

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Priority": 52
    }

For more information, see `Assigning job priority <https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-job-priority.html>`__ in the *Amazon S3 User Guide*.
