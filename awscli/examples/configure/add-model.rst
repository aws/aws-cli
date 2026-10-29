**To add a model**

The following ``add-model`` example adds a service model from a file named ``service.json``. ::

    aws configure add-model \
        --service-model file://service.json

Contents of ``service.json``::

    {
        "version": "2.0",
        "metadata": {
            "apiVersion": "2023-01-01",
            "endpointPrefix": "service",
            "jsonVersion": "1.1",
            "protocol": "json",
            "serviceFullName": "Example Service",
            "serviceId": "Service",
            "signatureVersion": "v4",
            "signingName": "service",
            "targetPrefix": "ExampleService",
            "uid": "service-2023-01-01"
        },
        "operations": {
            "ListWidgets": {
                "name": "ListWidgets",
                "http": {
                    "method": "POST",
                    "requestUri": "/"
                },
                "input": {
                    "shape": "ListWidgetsRequest"
                },
                "output": {
                    "shape": "ListWidgetsResponse"
                }
            }
        },
        "shapes": {
            "ListWidgetsRequest": {
                "type": "structure",
                "members": {
                    "MaxResults": {
                        "shape": "Integer"
                    }
                }
            },
            "ListWidgetsResponse": {
                "type": "structure",
                "members": {
                    "Widgets": {
                        "shape": "WidgetList"
                    }
                }
            },
            "WidgetList": {
                "type": "list",
                "member": {
                    "shape": "String"
                }
            },
            "Integer": {
                "type": "integer"
            },
            "String": {
                "type": "string"
            }
        }
    }

This command produces no output.

Adding a model replaces existing commands for the service defined in the model. To leave existing commands as-is, specify a different service name to use for the new commands. ::

    aws configure add-model \
        --service-model file://service.json \
        --service-name service2

For more information, see `Configuring settings for the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html>`__ in the *AWS CLI User Guide*.
