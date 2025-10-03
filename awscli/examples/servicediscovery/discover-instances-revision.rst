**Example 1: To discover the revision of an instance**

The following ``discover-instances-revision`` example discovers the increasing revision of an instance. ::

    aws servicediscovery discover-instances-revision \
        --namespace-name example.com \
        --service-name myservice

Output::

    {
        "InstancesRevision": 123456
    }

For more information, see `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To discover the revision of instances from a specific owner account**

The following ``discover-instances-revision`` example discovers the revision of instances from a specific owner account. The owner-account parameter is necessary for instances in namespaces that are shared with your account. ::

    aws servicediscovery discover-instances-revision \
        --namespace-name shared-namespace \
        --service-name shared-service \
        --owner-account 123456789111

Output::

    {
        "InstancesRevision": 1234567890
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ and `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.
