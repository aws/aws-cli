**Example 1: To create a policy with a text source file for the JSON policy**

The following ``create-policy`` example creates a service control policy (SCP) named ``AllowAllS3Actions``. The policy contents are taken from a file on the local computer called ``policy.json``. ::

    aws organizations create-policy \
        --content file://policy.json \
        --name AllowAllS3Actions \
        --type SERVICE_CONTROL_POLICY \
        --description "Allows delegation of all S3 actions"

Contents of ``policy.json``::

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:*"
                ],
                "Resource": [
                    "*"
                ]
            }
        ]
    }

Output::

    {
        "Policy": {
            "Content": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:*\"],\"Resource\":[\"*\"]}]}",
            "PolicySummary": {
                "Arn": "arn:aws:organizations::o-exampleorgid:policy/service_control_policy/p-examplepolicyid111",
                "Description": "Allows delegation of all S3 actions",
                "Name": "AllowAllS3Actions",
                "Type": "SERVICE_CONTROL_POLICY"
            }
        }
    }

For more information, see `Creating organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_create.html>`__ in the *AWS Organizations User Guide*.

**Example 2: To create a policy with a JSON policy as a parameter**

The following ``create-policy`` example creates the same SCP, this time by embedding the policy contents as a JSON string in the parameter. The string must be escaped with backslashes before the double quotes to ensure that they are treated as literals in the parameter, which itself is surrounded by double quotes. ::

    aws organizations create-policy \
        --content "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:*\"],\"Resource\":[\"*\"]}]}" \
        --name AllowAllS3Actions \
        --type SERVICE_CONTROL_POLICY \
        --description "Allows delegation of all S3 actions"

Output::

    {
        "Policy": {
            "Content": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Action\":[\"s3:*\"],\"Resource\":[\"*\"]}]}",
            "PolicySummary": {
                "Arn": "arn:aws:organizations::o-exampleorgid:policy/service_control_policy/p-examplepolicyid111",
                "Description": "Allows delegation of all S3 actions",
                "Name": "AllowAllS3Actions",
                "Type": "SERVICE_CONTROL_POLICY"
            }
        }
    }

For more information, see `Creating organization policies with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_policies_create.html>`__ in the *AWS Organizations User Guide*.

