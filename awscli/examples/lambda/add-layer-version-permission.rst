**To add permissions to a layer version**

The following ``add-layer-version-permission`` example grants permission for the specified account to use version 1 of the layer ``my-layer``. ::

    aws lambda add-layer-version-permission \
        --layer-name my-layer \
        --statement-id xaccount \
        --action lambda:GetLayerVersion  \
        --principal 123456789111 \
        --version-number 1

Output::

    {
        "RevisionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Statement": "{\"Sid\":\"xaccount\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789111:root\"},\"Action\":\"lambda:GetLayerVersion\",\"Resource\":\"arn:aws:lambda:us-west-2:123456789012:layer:my-layer:1\"}"
    }

For more information, see `AWS Lambda Layers <https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html>`__ in the *AWS Lambda Developer Guide*.
