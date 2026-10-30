**To attach a policy to an IAM user**

The following ``put-user-policy`` example attaches a policy to the IAM user named ``Bob``. ::

    aws iam put-user-policy \
        --user-name Bob \
        --policy-name ExamplePolicy \
        --policy-document file://AdminPolicy.json

Contents of ``AdminPolicy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "*",
                "Resource": "*"
            }
        ]
    }

This command produces no output.

The policy is defined as a JSON document in the *AdminPolicy.json* file. (The file name and extension do not have significance.)

For more information, see `Adding and removing IAM identity permissions <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-attach-detach.html>`__ in the *AWS IAM User Guide*.