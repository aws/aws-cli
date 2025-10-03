**Example 1: To create a service using namespace ID**

The following ``create-service`` example creates a service. ::

    aws servicediscovery create-service \
        --name myservice \
        --namespace-id  ns-ylexjili4cdxy3xm \
        --dns-config "RoutingPolicy=MULTIVALUE,DnsRecords=[{Type=A,TTL=60}]"

Output::

    {
        "Service": {
            "Id": "srv-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "myservice",
            "NamespaceId": "ns-abcd1234xmpl5678",
            "DnsConfig": {
                "NamespaceId": "ns-abcd1234xmpl5678",
                "RoutingPolicy": "MULTIVALUE",
                "DnsRecords": [
                    {
                        "Type": "A",
                        "TTL": 60
                    }
                ]
            },
            "Type": "DNS_HTTP",
            "CreateDate": "2025-08-18T13:45:31.023000-05:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678",
            "CreatedByAccount": "123456789012"
        }
    }

For more information, see `Creating an AWS Cloud Map service for an application component <https://docs.aws.amazon.com/cloud-map/latest/dg/creating-services.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To create a service using namespace ARN**

The following ``create-service`` example creates a service using a namespace ARN instead of namespace ID. Specifying a namespace ARN is necessary when creating a service in a shared namespace. ::

    aws servicediscovery create-service \
        --name myservice-arn \
        --namespace-id arn:aws:servicediscovery:us-west-2:123456789012:namespace/ns-abcd1234xmpl5678 \
        --dns-config "RoutingPolicy=MULTIVALUE,DnsRecords=[{Type=A,TTL=60}]"

Output::

    {
        "Service": {
            "Id": "srv-abcd1234xmpl5678",
            "Arn": "arn:aws:servicediscovery:us-west-2:123456789012:service/srv-abcd1234xmpl5678",
            "ResourceOwner": "123456789012",
            "Name": "myservice-arn",
            "NamespaceId": "ns-abcd1234xmpl5678",
            "DnsConfig": {
                "NamespaceId": "ns-abcd1234xmpl5678",
                "RoutingPolicy": "MULTIVALUE",
                "DnsRecords": [
                    {
                        "Type": "A",
                        "TTL": 60
                    }
                ]
            },
            "Type": "DNS_HTTP",
            "CreateDate": "2025-08-18T13:45:31.023000-05:00",
            "CreatorRequestId": "abcd1234-5678-90ab-cdef-xmpl12345678",
            "CreatedByAccount": "123456789012"
        }
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.

