**Example 1: To register a service instance using service ID**

The following ``register-instance`` example registers a service instance. ::

    aws servicediscovery register-instance \
        --service-id srv-p5zdwlg5uvvzjita \
        --instance-id myservice-53 \
        --attributes=AWS_INSTANCE_IPV4=172.2.1.3,AWS_INSTANCE_PORT=808

Output::

    {
        "OperationId": "4yejorelbukcjzpnr6tlmrghsjwpngf4-k95yg2u7"
    }

To confirm that the operation succeeded, you can run ``get-operation``. For more information, see `get-operation <https://docs.aws.amazon.com/cli/latest/reference/servicediscovery/get-operation.html>`__ .

For more information about registering an instance, see `Registering a resource as an AWS Cloud Map service instance <https://docs.aws.amazon.com/cloud-map/latest/dg/registering-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To register a service instance using service ARN**

The following ``register-instance`` example registers a service instance using a service ARN. Specifying the ARN is required when registering instances in services that are shared with your account. ::

    aws servicediscovery register-instance \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita \
        --instance-id web-server-01 \
        --attributes=AWS_INSTANCE_IPV4=203.0.113.15,AWS_INSTANCE_PORT=80

Output::

    {
        "OperationId": "gv4g5meo7ndmkqjrhpn39wk42xmpl"
    }

For more information about cross-account namespace sharing, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ in the *AWS Cloud Map Developer Guide*.
