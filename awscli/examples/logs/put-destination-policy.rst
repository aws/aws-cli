**To Create or update an access policy associated with an existing destination**

The following ``put-destination-policy`` example creates an access policy associated with an existing destination named ``demo-destination``. If the command succeeds, no output is returned. ::

    aws logs put-destination-policy \
        --destination-name "demo-destination" \
        --access-policy file://policy.json

The file ``policy.json`` is a JSON document in the current folder.

    {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "logs:*",
            "Resource": "arn:aws:logs:us-east-1:123456789012:destination:demo-destination",
            "Condition": {
                "StringEquals": {
                    "aws:PrincipalOrgID": ["o-abc123"]
                }
            }
        }]
    }

For more information, see `Cross-account cross-Region subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html>`__ in the *Amazon CloudWatch Logs User Guide*.