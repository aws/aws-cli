Get and put a bucket policy
---------------------------

The following example shows how you can download an Amazon S3 bucket policy,
make modifications to the file, and then use ``put-bucket-policy`` to
apply the modified bucket policy.  To download the bucket policy to a file,
you can run::

  aws s3api get-bucket-policy --bucket mybucket --query Policy --output text > policy.json

You can then modify the ``policy.json`` file as needed.  Finally you can apply
this modified policy back to the S3 bucket by running::

  aws s3api put-bucket-policy --bucket mybucket --policy file://policy.json
