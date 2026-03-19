**Example 1: To get the attributes of a service**

The following ``get-service-attributes`` example gets the attributes of a service. ::

    aws servicediscovery get-service-attributes \
        --service-id srv-abcd1234xmpl5678

Output::

    {
        "ServiceAttributes": {
            "ServiceArn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Attributes": {
                "Port": "80"
            }
        }
    }

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get the attributes of a service using ARN**

The following ``get-service-attributes`` example gets the attributes of a service using its ARN. Specifying an ARN is necessary for getting attributes of a service created in a namespace shared with your account. ::

    aws servicediscovery get-service-attributes \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678

Output::

    {
        "ServiceAttributes": {
            "ServiceArn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Attributes": {
                "Port": "80"
            }
        }
    }

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
