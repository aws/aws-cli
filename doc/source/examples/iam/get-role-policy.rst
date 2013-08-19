**To get information about a policy attached to an IAM role**

The following ``get-role-policy`` commmand gets information about the specified policy attached to the role named ``Test-Role``::

  aws iam get-role-policy --role-name Test-Role --policy-name ExamplePolicy

Output::

    {
      "RoleName": "Test-Role",
      "PolicyDocument": {
          "Statement": [
              {
                  "Action": [
                      "s3:ListBucket",
                      "s3:Put*",
                      "s3:Get*",
                      "s3:*MultipartUpload*"
                  ],
                  "Resource": "*",
                  "Effect": "Allow",
                  "Sid": "1"
              }
          ]
      },
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      },
      "PolicyName": "ExamplePolicy"
    }
    
For more information, see `Creating a Role`_ in the *Using IAM* guide.

.. _Creating a Role: http://docs.aws.amazon.com/IAM/latest/UserGuide/creating-role.html

