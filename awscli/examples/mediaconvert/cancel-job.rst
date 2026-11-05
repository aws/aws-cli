**To cancel a job that is in a queue**

The following ``cancel-job`` example cancels the job with ID ``1234567891234-abc123``. You can't cancel a job that the service has started processing. ::

    aws mediaconvert cancel-job \
        --endpoint-url https://abcd1234.mediaconvert.region-name-1.amazonaws.com \
        --id 1234567891234-abc123

This command produces no output.

To get your account-specific endpoint, use ``describe-endpoints``, or send the command without the endpoint. The service returns an error and your endpoint.

For more information, see `Working with jobs <https://docs.aws.amazon.com/mediaconvert/latest/ug/working-with-jobs.html>`__ in the *AWS Elemental MediaConvert User Guide*.
