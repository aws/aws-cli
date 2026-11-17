**To create an Amazon S3 batch operations job**

The following ``create-job`` example creates an Amazon S3 batch operations job to tag objects as ``confidential` in the bucket ``employee-records``. ::

    aws s3control create-job \
        --account-id 123456789012 \
        --operation '{"S3PutObjectTagging": { "TagSet": [{"Key":"confidential", "Value":"true"}] }}' \
        --report '{"Bucket":"arn:aws:s3:::amzn-s3-demo-bucket2","Prefix":"batch-op-create-job", "Format":"Report_CSV_20180820","Enabled":true,"ReportScope":"AllTasks"}' \
        --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820","Fields":["Bucket","Key"]},"Location":{"ObjectArn":"arn:aws:s3:::amzn-s3-demo-bucket2/inv-report/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222.csv","ETag":"69f52a4e9f797e987155d9c8f5880897"}}' \
        --priority 42 \
        --role-arn arn:aws:iam::123456789012:role/S3BatchJobRole

Output::

    {
        "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Creating an S3 Batch Operations job <https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-create-job.html>`__ in the *Amazon S3 User Guide*.
