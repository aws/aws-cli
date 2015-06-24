**To enable an MFA device**

After you ran the ``create-virtual-mfa-device`` command to create a new virtual MFA device, you can then assign this MFA device to a user.
The following example assigns the MFA device with the serial number ``arn:aws:iam::210987654321:mfa/BobsMFADevice`` to the user ``Bob``.
The command also synchronizes the device with AWS by including the first two codes in sequence from the virtual MFA device::

  aws iam enable-mfa-device --user-name Bob --serial-number arn:aws:iam::210987654321:mfa/BobsMFADevice --authentication-code-1 123456 --authentication-code-2 789012


For more information, see `Using a Virtual MFA Device with AWS`_ in the *Using IAM* guide.

.. _`Using a Virtual MFA Device with AWS`: http://docs.aws.amazon.com/IAM/latest/UserGuide/Using_VirtualMFA.html