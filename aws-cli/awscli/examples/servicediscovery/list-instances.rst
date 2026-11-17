**Example 1: To list service instances**

The following ``list-instances`` example lists service instances. ::

    aws servicediscovery list-instances \
        --service-id srv-qzpwvt2tfqcegapy

Output::

    {
        "Instances": [
            {
                "Id": "i-06bdabbae60f65a4e",
                "Attributes": {
                    "AWS_INSTANCE_IPV4": "172.2.1.3",
                    "AWS_INSTANCE_PORT": "808"
                },
                "CreatedByAccount": "123456789012"
            }
        ],
        "ResourceOwner": "123456789012"
    }

For more information, see `Listing AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/listing-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To list service instances using service ARN**

The following ``list-instances`` example lists service instances using a service ARN instead of service ID. Specifying an ARN is required when listing instances associated with namespaces that are shared with your account. ::

    aws servicediscovery list-instances \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita

Output::

    {
        "ResourceOwner": "123456789012",
        "Instances": [
            {
                "Id": "web-server-01",
                "Attributes": {
                    "AWS_INSTANCE_IPV4": "203.0.113.15",
                    "AWS_INSTANCE_PORT": "80"
                },
                "CreatedByAccount": "123456789012"
            },
            {
                "Id": "web-server-02",
                "Attributes": {
                    "AWS_INSTANCE_IPV4": "203.0.113.16",
                    "AWS_INSTANCE_PORT": "80"
                },
                "CreatedByAccount": "123456789012"
            }
        ]
    }

For more information about cross-account namespace sharing, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`_ and `Listing AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/listing-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

