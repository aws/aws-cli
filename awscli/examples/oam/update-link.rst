**To change what types of data are shared from a source account to its linked monitoring account sink**

The following ``update-link`` example updates the link ``arn:aws:oam:us-west-2:123456789111:link/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222`` with resource types ``AWS::CloudWatch::Metric`` and ``AWS::Logs::LogGroup``. ::

    aws oam update-link \
        --identifier arn:aws:oam:us-west-2:123456789111:link/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --resource-types "AWS::CloudWatch::Metric" "AWS::Logs::LogGroup"

Output::

    {
        "Arn": "arn:aws:oam:us-west-2:123456789111:link/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "Label": "sourceAccount",
        "LabelTemplate": "sourceAccount",
        "ResourceTypes": [
            "AWS::CloudWatch::Metric",
            "AWS::Logs::LogGroup"
        ],
        "SinkArn": "arn:aws:oam:us-west-2:123456789012:sink/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Tags": {}
    }

For more information, see `CloudWatch cross-account observability <https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch-Unified-Cross-Account.html>`__ in the *Amazon CloudWatch User Guide*.