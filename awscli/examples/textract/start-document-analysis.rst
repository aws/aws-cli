**To start analyzing text in a multi-page document**

The following ``start-document-analysis`` example shows how to start asynchronous analysis of text in a multi-page document.

For Linux and macOS, use the following command. ::

    aws textract start-document-analysis \
        --document-location '{"S3Object":{"Bucket":"amzn-s3-demo-bucket","Name":"document"}}' \
        --feature-types '["TABLES","FORMS"]' \
        --notification-channel "SNSTopicArn=arn:snsTopic,RoleArn=roleArn"

For Windows, use the following command. ::

    aws textract start-document-analysis \
        --document-location "{\"S3Object\":{\"Bucket\":\"amzn-s3-demo-bucket\",\"Name\":\"document\"}}" \
        --feature-types "[\"TABLES\", \"FORMS\"]" \
        --notification-channel "SNSTopicArn=arn:snsTopic,RoleArn=roleArn"

Output::

    {
        "JobId": "df7cf32ebbd2a5de113535fcf4d921926a701b09b4e7d089f3aebadb41e0712b"
    }

For more information, see `Processing Documents Asynchronously <https://docs.aws.amazon.com/textract/latest/dg/async.html>`__ in the *Amazon Textract Developer Guide*.
