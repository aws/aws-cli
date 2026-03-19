**Example 1: To list namespaces**

The following ``list-namespaces`` example lists namespaces. ::

    aws servicediscovery list-namespaces

Output::

    {
        "Namespaces": [
            {
                "Id": "ns-abcd1234xmpl5678",
                "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678",
                "ResourceOwner": "123456789012",
                "Name": "local",
                "Type": "DNS_PRIVATE",
                "Properties": {
                    "DnsProperties": {
                        "HostedZoneId": "Z06752353VBUDTC32S84S",
                        "SOA": {}
                    },
                    "HttpProperties": {
                        "HttpName": "local"
                     }
                },
                "CreateDate": "2023-07-17T13:37:27.872000-05:00"
            },
            {
                "Id": "ns-abcd1234xmpl9012",
                "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl9012",
                "ResourceOwner": "123456789012",
                "Name": "My-second-namespace",
                "Type": "HTTP",
                "Description": "My second namespace",
                "Properties": {
                    "DnsProperties": {
                        "SOA": {}
                    },
                    "HttpProperties": {
                        "HttpName": "My-second-namespace"
                    }
                },
                "CreateDate": "2023-11-14T10:35:47.840000-06:00"
            }
        ]
    }

For more information, see `Listing AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/listing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To list namespaces shared by other accounts**

The following ``list-namespaces`` example lists namespaces that are shared with the caller account by other AWS accounts using the ``RESOURCE_OWNER`` filter. ::

    aws servicediscovery list-namespaces \
        --filters Name=RESOURCE_OWNER,Values=OTHER_ACCOUNTS,Condition=EQ

Output::

    {
        "Namespaces": [
            {
                "Id": "ns-abcd1234xmpl5678",
                "Arn": "arn:aws:servicediscovery:us-west-2:123456789111:namespace/ns-abcd1234xmpl5678",
                "ResourceOwner": "123456789111",
                "Name": "shared-namespace",
                "Type": "HTTP",
                "Description": "Namespace shared from another account",
                "Properties": {
                    "DnsProperties": {
                        "SOA": {}
                    },
                    "HttpProperties": {
                        "HttpName": "shared-namespace"
                    }
                },
                "CreateDate": "2025-01-13T13:35:21.874000-06:00"
            }
        ]
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.