**To list recommendation resources**

The following ``list-recommendation-resources`` example lists all resources for a recommendation by its identifier. ::

    aws trustedadvisor list-recommendation-resources \
        --recommendation-identifier arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "recommendationResourceSummaries": [
            {
                "arn": "arn:aws:trustedadvisor::123456789012:recommendation-resource/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/18959a1f1973cff8e706e9d9bde28bba36cd602a6b2cb86c8b61252835236010",
                "id": "18959a1f1973cff8e706e9d9bde28bba36cd602a6b2cb86c8b61252835236010",
                "awsResourceId": "webcms-dev-01",
                "lastUpdatedAt": "2023-11-01T15:09:51.891Z",
                "metadata": {
                    "0": "14",
                    "1": "123.12000000000002",
                    "2": "webcms-dev-01",
                    "3": "db.m6i.large",
                    "4": "false",
                    "5": "us-west-2",
                    "6": "arn:aws:rds:us-west-2:123456789012:db:webcms-dev-01",
                    "7": "20"
                },
                "recommendationArn": "arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "regionCode": "us-west-2",
                "status": "warning"
            },
            {
                "arn": "arn:aws:trustedadvisor::123456789012:recommendation-resource/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/e6367ff500ac90db8e4adeb4892e39ee9c36bbf812dcbce4b9e4fefcec9eb63e",
                "id": "e6367ff500ac90db8e4adeb4892e39ee9c36bbf812dcbce4b9e4fefcec9eb63e",
                "awsResourceId": "aws-dev-db-stack-instance-1",
                "lastUpdatedAt": "2023-11-01T15:09:51.891Z",
                "metadata": {
                    "0": "14",
                    "1": "29.52",
                    "2": "aws-dev-db-stack-instance-1",
                    "3": "db.t2.small",
                    "4": "false",
                    "5": "us-west-2",
                    "6": "arn:aws:rds:us-west-2:123456789012:db:aws-dev-db-stack-instance-1",
                    "7": "1"
                },
                "recommendationArn": "arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "regionCode": "us-west-2",
                "status": "warning"
            },
            {
                "arn": "arn:aws:trustedadvisor::123456789012:recommendation-resource/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/31aa78ba050a5015d2d38cca7f5f1ce88f70857c4e1c3ad03f8f9fd95dad7459",
                "id": "31aa78ba050a5015d2d38cca7f5f1ce88f70857c4e1c3ad03f8f9fd95dad7459",
                "awsResourceId": "aws-awesome-apps-stack-db",
                "lastUpdatedAt": "2023-11-01T15:09:51.891Z",
                "metadata": {
                    "0": "14",
                    "1": "114.48000000000002",
                    "2": "aws-awesome-apps-stack-db",
                    "3": "db.m6g.large",
                    "4": "false",
                    "5": "us-west-2",
                    "6": "arn:aws:rds:us-west-2:123456789012:db:aws-awesome-apps-stack-db",
                    "7": "100"
                },
                "recommendationArn": "arn:aws:trustedadvisor::123456789012:recommendation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "regionCode": "us-west-2",
                "status": "warning"
            }
        ],
        "nextToken": "REDACTED"
    }

For more information, see `Get started with the Trusted Advisor API <https://docs.aws.amazon.com/awssupport/latest/user/get-started-with-aws-trusted-advisor-api.html>`__ in the *AWS Trusted Advisor User Guide*.