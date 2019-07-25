**To retrieve a Lambda function definition**

The following ``get-function-definition`` example retrieves the definition for the specified Lambda function. ::

    aws greengrass get-function-definition \
        --function-definition-id "063f5d1a-1dd1-40b4-9b51-56f8993d0f85"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/063f5d1a-1dd1-40b4-9b51-56f8993d0f85",
        "CreationTimestamp": "2019-06-18T16:21:21.431Z",
        "Id": "063f5d1a-1dd1-40b4-9b51-56f8993d0f85",
        "LastUpdatedTimestamp": "2019-06-18T16:21:21.431Z",
        "LatestVersion": "9748fda7-1589-4fcc-ac94-f5559e88678b",
        "LatestVersionArn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/063f5d1a-1dd1-40b4-9b51-56f8993d0f85/versions/9748fda7-1589-4fcc-ac94-f5559e88678b",
        "tags": {}
    }
