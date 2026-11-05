**To start detecting text in a multi-page document**

The following ``start-document-text-detection`` example shows how to start asynchronous detection of text in a multi-page document.

For Linux and macOS, use the following command. ::

    aws textract start-document-text-detection \
        --document-location '{"S3Object":{"Bucket":"amzn-s3-demo-bucket","Name":"document"}}' \
        --notification-channel "SNSTopicArn=arn:snsTopic,RoleArn=roleARN"

For Windows, use the following command. ::

    aws textract start-document-text-detection \
        --document-location "{\"S3Object\":{\"Bucket\":\"amzn-s3-demo-bucket\",\"Name\":\"document\"}}" \
        --notification-channel "SNSTopicArn=arn:snsTopic,RoleArn=roleArn"

Output::

    {
        "JobId": "57849a3dc627d4df74123dca269d69f7b89329c870c65bb16c9fd63409d200b9"
    }

For more information, see `Processing Documents Asynchronously <https://docs.aws.amazon.com/textract/latest/dg/async.html>`__ in the *Amazon Textract Developer Guide*.
