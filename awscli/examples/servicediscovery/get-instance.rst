**Example 1: To get the details of an instance**

The following ``get-instance`` example gets the attributes of a service. ::

    aws servicediscovery get-instance \
        --service-id srv-e4anhexample0004
        --instance-id i-abcd1234

Output::

    {  
        "ResourceOwner": "123456789012", 
        "Instance": {
            "Id": "arn:aws:servicediscovery:us-west-2:111122223333;:service/srv-e4anhexample0004",
            "Attributes": {
                "AWS_INSTANCE_IPV4": "192.0.2.44",
                "AWS_INSTANCE_PORT": "80",
                "color": "green",
                "region": "us-west-2",
                "stage": "beta"
            },
            "CreatedByAccount": "123456789012"
        }
    }

For more information, see `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get the details of an instance using service ARN for shared namespaces**

The following ``get-instance`` example gets the attributes of an instance using a service ARN instead of service ID. Specifying an ARN is required when getting details of instances associated with namespaces that are shared with your account. The instance returned in this example was registered by account ``123456789111`` in a namespace owned by account ``123456789012``. ::

    aws servicediscovery get-instance \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita \
        --instance-id web-server-01

Output::

    {
        "ResourceOwner": "123456789012",
        "Instance": {
            "Id": "web-server-01",
            "Attributes": {
                "AWS_INSTANCE_IPV4": "203.0.113.15",
                "AWS_INSTANCE_PORT": "80"
            },
            "CreatedByAccount": "123456789111"
        }
    }

For more information about cross-account namespace sharing, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
