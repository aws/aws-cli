**To deactivate an MFA device**

The following ``deactivate-mfa-device`` example deactivates the virtual MFA device with the ARN ``arn:aws:iam::123456789012:mfa/BobsMFADevice`` that is associated with the user ``Bob``. ::

    aws iam deactivate-mfa-device \
        --user-name Bob \
        --serial-number arn:aws:iam::123456789012:mfa/BobsMFADevice

This command produces no output.

For more information, see `Using multi-factor authentication (MFA) in AWS <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html>`__ in the *AWS IAM User Guide*.