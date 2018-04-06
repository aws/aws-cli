**To cancel a job that is in a queue**

The following example cancels the job with ID 1234567891234-abc123. You can't cancel a job that the service has started processing:

Command::
     aws --endpoint-url=https://abcd1234.mediaconvert.region-name-1.amazonaws.com --region=region-name-1 mediaconvert cancel-job --id=1234567891234-abc123