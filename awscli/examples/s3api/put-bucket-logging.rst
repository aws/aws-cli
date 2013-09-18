The example below sets the logging policy for *MyBucket*. The AWS user *user@example.com* will have full control over
the log files, and all users will have access to them::

   aws s3api put-bucket-acl --bucket MyBucket --grant-write 'URI="http://acs.amazonaws.com/groups/s3/LogDelivery"' --grant-read-acp 'URI="http://acs.amazonaws.com/groups/s3/LogDelivery"'

   aws s3api put-bucket-logging --bucket MyBucket --bucket-logging-status file://logging.json

   logging.json:
   {
     "LoggingEnabled": {
       "TargetBucket": "MyBucket",
       "TargetPrefix": "MyBucketLogs/",
       "TargetGrants": [
         {
           "Grantee": {
             "Type": "AmazonCustomerByEmail",
             "EmailAddress": "user@example.com"
           },
           "Permission": "FULL_CONTROL"
         },
         {
           "Grantee": {
             "Type": "Group",
             "URI": "http://acs.amazonaws.com/groups/global/AllUsers"
           },
           "Permission": "READ"
         }
       ]
     }
   }

.. note:: the ``put-bucket-acl`` command is required to grant S3's log delivery system the necessary permissions (write
   and read-acp permissions).
