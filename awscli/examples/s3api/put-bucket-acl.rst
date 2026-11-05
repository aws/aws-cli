**To set the access control list for a bucket**

The following ``put-bucket-acl`` example grants ``full control`` to two AWS users (*user1@example.com* and *user2@example.com*) and ``read``
permission to everyone. ::

    aws s3api put-bucket-acl \
        --bucket amzn-s3-demo-bucket \
        --grant-full-control emailaddress=user1@example.com,emailaddress=user2@example.com \
        --grant-read uri=http://acs.amazonaws.com/groups/global/AllUsers

This command produces no output.

For more information, see `Configuring ACLs <https://docs.aws.amazon.com/AmazonS3/latest/userguide/managing-acls.html>`__ in the *Amazon S3 User Guide*.
