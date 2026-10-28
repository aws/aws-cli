**To set the access control list for a bucket**

The following ``put-bucket-acl`` example grants ``full control`` to two AWS users (*user1@example.com* and *user2@example.com*) and ``read``
permission to everyone. This command produces no output. ::

    aws s3api put-bucket-acl \
        --bucket amzn-s3-demo-bucket \
        --grant-full-control emailaddress=user1@example.com,emailaddress=user2@example.com \
        --grant-read uri=http://acs.amazonaws.com/groups/global/AllUsers

See http://docs.aws.amazon.com/AmazonS3/latest/API/RESTBucketPUTacl.html for details on custom ACLs (the s3api ACL
commands, such as ``put-bucket-acl``, use the same shorthand argument notation).

