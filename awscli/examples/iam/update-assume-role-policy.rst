**To update the trust policy for an IAM role**

The following ``update-assume-role-policy`` example updates the trust policy for the role named ``Test-Role``. ::

    aws iam update-assume-role-policy \
        --role-name Test-Role \
        --policy-document file://Test-Role-Trust-Policy.json

Contents of ``Test-Role-Trust-Policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "Statement1",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::123456789012:root"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

This command produces no output.

The trust policy is defined as a JSON document in the *Test-Role-Trust-Policy.json* file. (The file name and extension
do not have significance.) The trust policy must specify a principal.

To update the permissions policy for a role, use the ``put-role-policy`` command.

For more information, see `Creating IAM roles <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create.html>`__ in the *AWS IAM User Guide*.