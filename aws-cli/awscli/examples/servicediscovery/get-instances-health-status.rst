**Example 1: To get the health status of instances associated with a service**

The following ``get-instances-health-status`` example gets the health status of instances associated with the specified service. ::

    aws servicediscovery get-instances-health-status \
        --service-id srv-e4anhexample0004

Output::

    {
        "Status": {
            "i-abcd1234": "HEALTHY",
            "i-abcd1235": "UNHEALTHY"
        }
    }

For more information, see `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To get the health status of instances using service ARN for shared namespaces**

The following ``get-instances-health-status`` example gets the health status of instances using a service ARN instead of service ID. Specifying an ARN is required when getting health status for instances associated with namespaces that are shared with the requester's account. ::

    aws servicediscovery get-instances-health-status \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita

Output::

    {
        "Status": {
            "web-server-01": "HEALTHY",
            "web-server-02": "UNHEALTHY"
        }
    }

For more information, see `AWS Cloud Map service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/working-with-instances.html>`__ and `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
