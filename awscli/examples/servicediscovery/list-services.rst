**Example 1: To list services**

The following ``list-services`` example lists services. ::

    aws servicediscovery list-services

Output::

    {
        "Services": [
            {
                "Id": "srv-p5zdwlg5uvvzjita",
                "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita",
                "Name": "myservice",
                "DnsConfig": {
                    "RoutingPolicy": "MULTIVALUE",
                    "DnsRecords": [
                        {
                            "Type": "A",
                            "TTL": 60
                        }
                    ]
                },
                "CreateDate": 1587081768.334
            }
        ]
    }

For more information, see `Listing AWS Cloud Map services in a namespace <https://docs.aws.amazon.com/cloud-map/latest/dg/listing-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To list services created in shared namespaces**

The following ``list-services`` example lists services that are created in namespaces shared with the caller account ``123456789012`` by other AWS accounts using the ``RESOURCE_OWNER`` filter. ::

    aws servicediscovery list-services \
        --filters Name=RESOURCE_OWNER,Values=OTHER_ACCOUNTS,Condition=EQ

Output::

    {
        "Services": [
            {
                "Id": "srv-abcd1234xmpl5678",
                "Arn": "arn:aws:servicediscovery:us-west-2:123456789111:service/srv-abcd1234xmpl5678",
                "ResourceOwner": "123456789111",
                "Name": "shared-service",
                "NamespaceId": "ns-abcd1234xmpl5678",
                "Type": "HTTP",
                "Description": "Service in shared namespace",
                "DnsConfig": {},
                "CreateDate": "2025-01-13T13:35:21.874000-06:00",
                "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678",
                "CreatedByAccount": "123456789012"
            }
        ]
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ and `Listing AWS Cloud Map services in a namespace <https://docs.aws.amazon.com/cloud-map/latest/dg/listing-services.html>`__  in the *AWS Cloud Map Developer Guide*.
