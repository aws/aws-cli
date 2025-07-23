**To get a list of run caches**

The following ``list-run-caches`` example lists all existing run caches in the associated AWS HealthOmics account. ::

    aws omics list-run-caches

Output::

    {
        "items": [
            {
                "arn": "arn:aws:omics:us-west-2:123456789012:runCache/2743932",
                "cacheBehavior": "CACHE_ON_FAILURE",
                "cacheS3Uri": "s3://omics-output-us-west-2-123456789012/cache/decbe15f-2b59-88bb-6c6d-2759000b90a1/",
                "creationTime": "2025-06-30T21:29:03.406500+00:00",
                "id": "2743932",
                "status": "ACTIVE"
            },
            {
                "arn": "arn:aws:omics:us-west-2:123456789012:runCache/7038070",
                "cacheBehavior": "CACHE_ON_FAILURE",
                "cacheS3Uri": "s3://omics-output-us-west-2-123456789012/cache/30cbe158-d6cd-6e9e-2cf1-9e40ff641318/",
                "creationTime": "2025-06-30T21:15:13.683730+00:00",
                "id": "7038070",
                "status": "ACTIVE"
            },
        ]
    }

For more information, see `Call caching for HealthOmics runs <https://docs.aws.amazon.com/omics/latest/dev/workflows-call-caching.html>`__ in the *AWS HealthOmics User Guide*.
