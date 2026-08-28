**To view a run cache**

The following ``get-run-cache`` example retrieves metadata for the run cache ``1234567``. ::

    aws omics get-run-cache --id 1234567

Output::

    {
        "arn": "arn:aws:omics:us-west-2:123456789012:runCache/1234567",
        "cacheBehavior": "CACHE_ON_FAILURE",
        "cacheS3Uri": "s3://omics-output-us-west-2-123456789012/cache/decbe15f-2b59-88bb-6c6d-2759000b90a1/",
        "creationTime": "2025-06-30T21:29:03.406500+00:00",
        "id": "1234567",
        "status": "ACTIVE",
        "tags": {}
    }

For more information, see `Contents of a run cache <https://docs.aws.amazon.com/omics/latest/dev/workflow-cache-contents.html>`__ in the *AWS HealthOmics User Guide*.
