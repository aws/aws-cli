**To create a logging configuration for the web ACL ARN with the specified Kinesis Firehose stream ARN**

The following ``put-logging-configuration`` example displays logging configuration for WAF with ALB/APIGateway in Region ``us-west-2``. ::

    aws waf-regional put-logging-configuration \
        --logging-configuration ResourceArn=arn:aws:waf-regional:us-west-2:123456789012:webacl/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111,LogDestinationConfigs=arn:aws:firehose:us-west-2:123456789012:deliverystream/aws-waf-logs-firehose-stream,RedactedFields=[]

Output::

    {
        "LoggingConfiguration": {
            "ResourceArn": "arn:aws:waf-regional:us-west-2:123456789012:webacl/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "LogDestinationConfigs": [
                "arn:aws:firehose:us-west-2:123456789012:deliverystream/aws-waf-logs-firehose-stream"
            ]
        }
    }

For more information, see `Logging Web ACL traffic information <https://docs.aws.amazon.com/waf/latest/developerguide/classic-logging.html>`__ in the *AWS WAF, AWS Firewall Manager, and AWS Shield Advanced Developer Guide*.
