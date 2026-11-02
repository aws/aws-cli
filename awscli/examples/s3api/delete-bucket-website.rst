**To delete the website configuration of a bucket**

The following ``delete-bucket-website`` example deletes a website configuration from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-website \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Hosting a static website using Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html>`__ in the *Amazon S3 User Guide*.
