**To set the access control list for an object**

The following ``put-object-acl`` example grants ``full control`` to two AWS users (*user1@example.com* and *user2@example.com*) and ``read``
permission to everyone. ::

    aws s3api put-object-acl \
        --bucket amzn-s3-demo-bucket \
        --key file.txt \
        --grant-full-control emailaddress=user1@example.com,emailaddress=user2@example.com \
        --grant-read uri=http://acs.amazonaws.com/groups/global/AllUsers

This command produces no output.

For more information, see `Access control list (ACL) overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html>`__ in the *Amazon S3 User Guide*.
