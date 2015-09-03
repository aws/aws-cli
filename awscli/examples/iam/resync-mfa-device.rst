**To synchronize the specified MFA device with AWS servers**

This example synchronizes the MFA device that is associated with the IAM user ``Bob`` and whose ARN is ``arn:aws:iam::123456789012:mfa/BobsMFADevice`` 
with an authenticator program that provided the two authentication codes::

  aws iam resync-mfa-device --user-name Bob --serial-number arn:aws:iam::210987654321:mfa/BobsMFADevice --authentication-code-1 123456 --authentication-code-2 987654


For more information, see `Using Multi-Factor Authentication (MFA) Devices with AWS`_ in the *IAM User* guide.

.. _`Using Multi-Factor Authentication (MFA) Devices with AWS`: http://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html