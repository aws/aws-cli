**Example 1: To get the settings of a service**

The following ``get-service`` example gets the settings of a specified service. ::

    aws servicediscovery get-service \
        --id srv-abcd1234xmpl5678

Output::

    {
        "Service": {
            "Id": "srv-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "test-service",
            "NamespaceId": "ns-abcd1234xmpl5678",
            "DnsConfig": {},
            "Type": "HTTP",
            "CreateDate": "2025-08-18T13:53:02.775000-05:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678",
            "CreatedByAccount": "123456789012"
        }
    }

For more information, see `AWS Cloud Map services <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get the settings of a service using ARN**

The following ``get-service`` example gets the settings of a specified service using its ARN. Specifying the ARN is necessary when retrieving information about a service created in a namespace that is shared with your account. The caller account ``123456789111`` created the service in a namespace shared by account ``123456789012``. ::

    aws servicediscovery get-service \
        --id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678

Output::

    {
        "Service": {
            "Id": "srv-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "test-service",
            "NamespaceId": "ns-abcd1234xmpl5678",
            "DnsConfig": {},
            "Type": "HTTP",
            "CreateDate": "2025-08-18T13:53:02.775000-05:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678",
            "CreatedByAccount": "123456789111"
        }
    }

For more information, see `Creating an AWS Cloud Map service for an application component <https://docs.aws.amazon.com/cloud-map/latest/dg/creating-services.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
