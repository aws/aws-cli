The example below sets the logging policy for *MyBucket*. The AWS user *bob@example.com* will have full control over
the log files, and no one else has any access. First, grant S3 permission with ``put-bucket-acl``::

   aws s3api put-bucket-acl --bucket MyBucket --grant-write URI=http://acs.amazonaws.com/groups/s3/LogDelivery --grant-read-acp URI=http://acs.amazonaws.com/groups/s3/LogDelivery

Then apply the logging policy::

   aws s3api put-bucket-logging --bucket MyBucket --bucket-logging-status file://logging.json

``logging.json`` is a JSON document in the current folder that contains the logging policy::

    {
      "LoggingEnabled": {
        "TargetBucket": "MyBucket",
        "TargetPrefix": "MyBucketLogs/",
        "TargetGrants": [
          {
            "Grantee": {
              "Type": "AmazonCustomerByEmail",
              "EmailAddress": "bob@example.com"
            },
            "Permission": "FULL_CONTROL"
          }
        ]
      }
    }

.. note:: the ``put-bucket-acl`` command is required to grant S3's log delivery system the necessary permissions (write
   and read-acp permissions).

For more information, see `Amazon S3 Server Access Logging <https://docs.aws.amazon.com/AmazonS3/latest/dev/ServerLogs.html>`__ in the *Amazon S3 Developer Guide*.
