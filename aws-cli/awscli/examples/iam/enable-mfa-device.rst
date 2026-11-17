**To enable an MFA device**

The following ``enable-mfa-device`` example assigns the MFA device with the serial number ``arn:aws:iam::123456789012:mfa/BobsMFADevice`` to the user ``Bob``. The command also synchronizes the device with AWS by including the first two codes in sequence from the virtual MFA device. Before you assign a virtual MFA device to a user, you create it by using the ``create-virtual-mfa-device`` command. ::

    aws iam enable-mfa-device \
        --user-name Bob \
        --serial-number arn:aws:iam::123456789012:mfa/BobsMFADevice \
        --authentication-code1 123456 \
        --authentication-code2 789012

This command produces no output.

For more information, see `Enabling a virtual multi-factor authentication (MFA) device <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa_enable_virtual.html>`__ in the *AWS IAM User Guide*.