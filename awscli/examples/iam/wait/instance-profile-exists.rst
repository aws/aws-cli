**To pause running until the specified instance profile exists**

The following ``wait instance-profile-exists`` example pauses and continues only after it can confirm that the specified instance profile exists. ::

    aws iam wait instance-profile-exists \
        --instance-profile-name WebServer

This command produces no output.

For more information, see `Use instance profiles <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html>`__ in the *AWS IAM User Guide*.
