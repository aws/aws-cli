**To cancel a job**

The following ``cancel-job`` example cancels a job with the specified job ID. ::

    aws batch cancel-job \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --reason "Cancelling job."

This command produces no output.

For more information, see `Job states <https://docs.aws.amazon.com/batch/latest/userguide/job_states.html>`__ in the *AWS Batch User Guide*.
