**To add permissions to an existing Lambda function**

The following ``add-permission`` example grants the Amazon SNS service permission to invoke a function named ``my-function`` from topic  ``arn:aws:sns:us-east-2:123456789012:my-topic``::

    aws lambda add-permission \
        --function-name my-function \
        --action lambda:InvokeFunction \
        --statement-id sns \
        --principal sns.amazonaws.com \
        --source-arn arn:aws:sns:us-east-2:123456789012:my-topic

Output::

    {
        "Statement":
        {
            "Sid":"sns",
            "Effect":"Allow",
            "Principal":{
                "Service":"sns.amazonaws.com"
            },
            "Action":"lambda:InvokeFunction",
            "Resource":"arn:aws:lambda:us-east-2:123456789012:function:my-function",
            "Condition": {
                "ArnLike": {
                    "AWS:SourceArn": "arn:aws:sns:us-east-2:123456789012:my-topic"
                }
            }
        }
    }

For more information, see `Using Resource-based Policies for AWS Lambda <https://docs.aws.amazon.com/lambda/latest/dg/access-control-resource-based.html>`__ in the *AWS Lambda Developer Guide*.
