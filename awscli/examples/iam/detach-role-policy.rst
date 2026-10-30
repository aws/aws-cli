**To detach a policy from a role**

The following ``detach-role-policy`` example removes the managed policy with the ARN ``arn:aws:iam::123456789012:policy/FederatedTesterAccessPolicy`` from the role called ``FedTesterRole``. ::

    aws iam detach-role-policy \
        --role-name FedTesterRole \
        --policy-arn arn:aws:iam::123456789012:policy/FederatedTesterAccessPolicy 

This command produces no output.

For more information, see `IAM role management <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_manage.html>`__ in the *AWS IAM User Guide*.