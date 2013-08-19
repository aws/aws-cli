**To remove a virtual MFA device**

The following ``delete-virtual-mfa-device`` commmand remmoves the specified MFA device from the current account::

  aws iam delete-virtual-mfa-device --serial-number arn:aws:iam::123456789012:mfa/MFATest

Output::

  {
      "ResponseMetadata": {
          "RequestId": "b9cd3e32-4a54-11e2-8110-65075b2814da"
      }
  }    

For more information, see `Using a Virtual MFA Device with AWS`_ in the *Using IAM* guide.

.. _Using a Virtual MFA Device with AWS: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_VirtualMFA.html

