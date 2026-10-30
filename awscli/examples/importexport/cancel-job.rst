**To cancel a job**

The following ``cancel-job`` example cancels the specified job. ::

    aws importexport cancel-job \
        --job-id EX1ID

Output::

    {
        "Success": true
    }

Only jobs that were created by the AWS account you're currently using can be canceled. Jobs that have already completed cannot be canceled.
