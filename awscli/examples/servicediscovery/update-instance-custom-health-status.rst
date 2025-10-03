**Example 1: To update a custom health check**

The following ``update-instance-custom-health-status`` example updates the status of the custom health check for the specified service and example service instance to ``HEALTHY``. ::

    aws servicediscovery update-instance-custom-health-status \
        --service-id srv-e4anhexample0004 \
        --instance-id example \
        --status HEALTHY

This command produces no output.

For more information, see `AWS Cloud Map service health check configuration <https://docs.aws.amazon.com/cloud-map/latest/dg/services-health-checks.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To update a custom health check using service ARN**

The following ``update-instance-custom-health-status`` example updates the status of the custom health check using a service ARN. The ARN is required when updating health status for instances associated with namespaces that are shared with the your account. ::

    aws servicediscovery update-instance-custom-health-status \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita \
        --instance-id web-server-01 \
        --status HEALTHY

This command produces no output.

For more information, see `AWS Cloud Map service health check configuration <https://docs.aws.amazon.com/cloud-map/latest/dg/services-health-checks.html>`__ and `Cross-account AWS Cloud Map namespace sharing <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
