The following command creates a customer managed policy named ``my-policy``::

  aws iam create-policy --policy-name my-policy --policy-document file://policy

Output::

  {
      "Policy": {
          "PolicyName": "my-policy",
          "CreateDate": "2015-06-01T19:31:18.620Z",
          "AttachmentCount": 0,
          "IsAttachable": true,
          "PolicyId": "ZXR6A36LTYANPAI7NJ5UV",
          "DefaultVersionId": "v1",
          "Path": "/",
          "Arn": "arn:aws:iam::0123456789012:policy/my-policy",
          "UpdateDate": "2015-06-01T19:31:18.620Z"
      }
  }

The file ``policy`` is a JSON document in the current folder that grants read only access to the ``shared`` folder in an Amazon S3 bucket named ``my-bucket``::

  {
      "Version": "2012-10-17",
      "Statement": [
          {
              "Effect": "Allow",
              "Action": [
                  "s3:Get*",
                  "s3:List*"
              ],
              "Resource": [
                  "arn:aws:s3:::my-bucket/shared/*"
              ]
          }
      ]
  }

For more information on using files as input for string parameters, see `Specifying Parameter Values`_ in the *AWS CLI User Guide*.

.. _`Specifying Parameter Values`: http://docs.aws.amazon.com/cli/latest/userguide/cli-using-param.html
