**To Get A Control Tower Baseline Operation**

The following ``get-baseline-operation`` example get details of an AWS Control Tower baseline operation::

    aws controltower get-baseline-operation \
        --operation-identifier "51e190ac-8a37-4f6d-b63c-fb5104b5db38"

Output::

    {
        "baselineOperation": {
            "endTime": "2025-04-17T23:48:46+00:00",
            "operationIdentifier": "51e190ac-8a37-4f6d-b63c-fb5104b5db38",
            "operationType": "ENABLE_BASELINE",
            "startTime": "2025-04-17T23:46:37+00:00",
            "status": "SUCCEEDED",
            "statusMessage": "AWS Control Tower completed the baseline operation successfully."
        }
    }

For more information, see `AWS Control Tower Baselines <https://docs.aws.amazon.com/controltower/latest/userguide/types-of-baselines.html>`__ in the *AWS Control Tower User Guide*.