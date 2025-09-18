**Example 1: To discover registered instances**

The following ``discover-instances`` example discovers registered instances. ::

    aws servicediscovery discover-instances \
        --namespace-name example.com \
        --service-name myservice \
        --max-results 10 \
        --health-status ALL

Output::

    {
        "Instances": [
            {
                "InstanceId": "myservice-53",
                "NamespaceName": "example.com",
                "ServiceName": "myservice",
                "HealthStatus": "UNKNOWN",
                "Attributes": {
                    "AWS_INSTANCE_IPV4": "172.2.1.3",
                    "AWS_INSTANCE_PORT": "808"
                }
            }
        ],
        "InstancesRevision": 85648075627387284
    }

For more information, see `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To discover instances from a specific owner account**

The following ``discover-instances`` example discovers registered instances from a specific owner account. This parameter is necessary to discover instances in namespaces that are shared with your account. ::

    aws servicediscovery discover-instances \
        --namespace-name shared-namespace \
        --service-name shared-service \
        --owner-account 123456789111

Output::

    {
        "Instances": [
            {
                "InstanceId": "shared-instance-1234",
                "NamespaceName": "shared-namespace",
                "ServiceName": "shared-service",
                "HealthStatus": "HEALTHY",
                "Attributes": {
                    "AWS_INSTANCE_IPV4": "203.0.113.75",
                    "AWS_INSTANCE_PORT": "80"
                }
            }
        ],
        "InstancesRevision": 1234567890
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ and `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.
