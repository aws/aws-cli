**To create a run cache**

The following ``create-run-cache`` example creates a run cache with a specified S3 location for storing the cached task outputs. ::

    aws omics create-run-cache \
    --cache-s3-location "s3://example-bucket/cache/"

Output::

    {
        "arn": "arn:aws:omics:us-west-2:123456789012:runCache/1234567",
        "id": "1234567",
        "status": "ACTIVE",
        "tags": {}
    }

For more information, see `Creating a run cache <https://docs.aws.amazon.com/omics/latest/dev/workflow-cache-create.html>`__ in the *AWS HealthOmics User Guide*.
