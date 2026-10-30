**To terminate a job**

The following ``terminate-job`` example terminates a job with the specified job ID. ::

    aws batch terminate-job \
        --job-id 61e743ed-35e4-48da-b2de-5c8333821c84 \
        --reason "Terminating job."

This command produces no output.

For more information, see `Job states <https://docs.aws.amazon.com/batch/latest/userguide/job_states.html>`__ in the *AWS Batch User Guide*.
