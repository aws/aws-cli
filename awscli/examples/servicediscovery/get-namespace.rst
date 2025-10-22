**Example 1: To get the details of a namespace**

The following ``get-namespace`` example retrieves information about the specified namespace. ::

    aws servicediscovery get-namespace \
        --id ns-abcd1234xmpl5678

Output::

    {
        "Namespace": {
            "Id": "ns-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "example-http.com",
            "Type": "HTTP",
            "Description": "Example.com AWS Cloud Map HTTP Namespace",
            "Properties": {
                "DnsProperties": {},
                "HttpProperties": {
                    "HttpName": "example-http.com"
                }
            },
            "CreateDate": "2024-02-23T13:35:21.874000-06:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678"
        }
    }

For more information, see `AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get the details of a namespace using ARN**

The following ``get-namespace`` example retrieves information about the specified namespace using its ARN. Specifying the ARN is necessary for retreiving details of a namespace shared with your account. ::

    aws servicediscovery get-namespace \
        --id arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678

Output::

    {
        "Namespace": {
            "Id": "ns-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "example-http.com",
            "Type": "HTTP",
            "Description": "Example.com AWS Cloud Map HTTP Namespace",
            "Properties": {
                "DnsProperties": {},
                "HttpProperties": {
                    "HttpName": "example-http.com"
                }
            },
            "CreateDate": "2024-02-23T13:35:21.874000-06:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678"
        }
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
