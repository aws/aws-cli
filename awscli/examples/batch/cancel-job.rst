**To cancel a job**

The following ``cancel-job`` example cancels a job with the specified job ID. ::

    aws batch cancel-job \
        --job-id bcf0b186-a532-4122-842e-2ccab8d54efb \
        --reason "Cancelling job."
