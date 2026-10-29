**To create a version of the function definition**

The following ``create-function-definition-version`` example creates a new version of the specified function definition. This version specifies a single function whose ID is ``Hello-World-function``, allows access to the file system, and specifies a maximum memory size and timeout period. ::

    aws greengrass create-function-definition-version \
        --cli-input-json "{\"FunctionDefinitionId\": \"a1b2c3d4-5678-90ab-cdef-EXAMPLE11111\",\"Functions\": [{\"Id\": \"Hello-World-function\", \"FunctionArn\": \""arn:aws:lambda:us-west-2:123456789012:function:Greengrass_HelloWorld_Counter:gghw-alias"\",\"FunctionConfiguration\": {\"Environment\": {\"AccessSysfs\": true},\"Executable\": \"greengrassHelloWorldCounter.function_handler\",\"MemorySize\": 16000,\"Pinned\": false,\"Timeout\": 25}}]}"

Output::

    {
        "Arn": "arn:aws:greengrass:us-west-2:123456789012:/greengrass/definition/functions/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/versions/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "CreationTimestamp": "2019-06-25T22:03:43.376Z",
        "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Version": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Run Lambda functions on the AWS IoT Greengrass core <https://docs.aws.amazon.com/greengrass/v1/developerguide/lambda-functions.html>`__ in the *AWS IoT Greengrass Developer Guide*.
