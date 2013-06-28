**To list virtual MFA devices**

The following ``list-virtual-mfa-devices`` commmand lists the virtual MFA devices that have been configured for the current account::

  aws iam list-virtual-mfa-devices

Output::

  [
      {
          "SerialNumber": "arn:aws:iam::123456789012:mfa/MFATest",
          "EnableDate": "2012-12-28T00:37:06Z",
          "User": {
              "UserName": "Bob",
              "Path": "/",
              "CreateDate": "2012-12-28T00:23:17Z",
              "UserId": "AKIAIOSFODNN7EXAMPLE",
              "Arn": "arn:aws:iam::123456789012:user/Bob"
          }
      }
  ]

For more information, see `Using a Virtual MFA Device with AWS`_ in the *Using IAM* guide.

.. _Using a Virtual MFA Device with AWS: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_VirtualMFA.html

