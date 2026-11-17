**To register the cross account access role**

The following ``register-cross-account-access-role`` example registers the IAM role with the ARN of ``arn:aws:iam::123456789012:role/inspector`` that Amazon Inspector uses to list your EC2 instances at the start of the assessment run or when you call the ``preview-agents`` command. ::

    aws inspector register-cross-account-access-role \
        --role-arn arn:aws:iam::123456789012:role/inspector

This command produces no output.

