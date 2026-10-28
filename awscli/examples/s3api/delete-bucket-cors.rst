**To delete the CORS configuration of a bucket**

The following ``delete-bucket-cors`` example deletes a Cross-Origin Resource Sharing configuration from a bucket named ``amzn-s3-demo-bucket``. This command produces no output. ::

    aws s3api delete-bucket-cors \
        --bucket amzn-s3-demo-bucket
