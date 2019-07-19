**To retrieve details about a specific version of a Lambda function**

The following ``get-function-definition-version`` example retrieves details for the specified version of a Lamba function. You can use the ``list-function-definitions`` command to get the ID for the latest version of a Lambda function. If you know the function ID, you can instead use ``get-function-definition``, which includes the latest version ID.  To view older versions of a function, use the ``list-function-definition-versions`` CLI command. ::

    aws greengrass get-function-definition-version \
        --function-definition-id "063f5d1a-1dd1-40b4-9b51-56f8993d0f85" \
        --function-definition-version-id "9748fda7-1589-4fcc-ac94-f5559e88678b"
    
Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/063f5d1a-1dd1-40b4-9b51-56f8993d0f85/versions/9748fda7-1589-4fcc-ac94-f5559e88678b",
        "CreationTimestamp": "2019-06-18T17:04:30.776Z",
        "Definition": {
            "Functions": [
                {
                    "FunctionArn": "arn:aws:lambda:::function:GGIPDetector:1",
                    "FunctionConfiguration": {
                        "Environment": {},
                        "MemorySize": 32768,
                        "Pinned": true,
                        "Timeout": 3
                    },
                    "Id": "26b69bdb-e547-46bc-9812-84ec04b6cc8c"
                },
                {
                    "FunctionArn": "arn:aws:lambda:us-west-2:123456789012:function:Greengrass_HelloWorld:GG_HelloWorld",
                    "FunctionConfiguration": {
                        "EncodingType": "json",
                        "Environment": {
                            "Variables": {}
                        },
                        "MemorySize": 16384,
                        "Pinned": true,
                        "Timeout": 25
                    },
                    "Id": "384465a8-eedf-48c6-b793-4c35f7bfae9b"
                }
            ]
        },
        "Id": "063f5d1a-1dd1-40b4-9b51-56f8993d0f85",
        "Version": "9748fda7-1589-4fcc-ac94-f5559e88678b"
    }
