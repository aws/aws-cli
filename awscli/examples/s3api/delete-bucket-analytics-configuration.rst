**To delete the analytics configuration of a bucket**

The following ``delete-bucket-analytics-configuration`` example deletes the analytics configuration of the specified bucket. ::

    aws s3api delete-bucket-analytics-configuration \
        --bucket my-bucket \
        --id 1

This command produces no output.
