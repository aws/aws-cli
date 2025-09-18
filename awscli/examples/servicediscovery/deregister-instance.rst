**Example 1: To deregister a service instance**

The following ``deregister-instance`` example deregisters a service instance. ::

    aws servicediscovery deregister-instance \
        --service-id srv-p5zdwlg5uvvzjita \
        --instance-id myservice-53

Output::

    {
        "OperationId": "4yejorelbukcjzpnr6tlmrghsjwpngf4-k98rnaiq"
    }

To confirm that the operation succeeded, you can run ``get-operation``. For more information, see `get-operation <https://docs.aws.amazon.com/cli/latest/reference/servicediscovery/get-operation.html>`__.

For more information, see `Deregistering service instances <https://docs.aws.amazon.com/cloud-map/latest/dg/deregistering-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

**Example 2: To deregister a service instance using service ARN for shared namespaces**

The following ``deregister-instance`` example deregisters a service instance using a service ARN instead of service ID. Specifying an ARN is required when deregistering instances from services created in namespaces that are shared with your account. ::

    aws servicediscovery deregister-instance \
        --service-id arn:aws:servicediscovery:us-west-2:123456789012:service/srv-p5zdwlg5uvvzjita \
        --instance-id web-server-01

Output::

    {
        "OperationId": "gv4g5meo7ndmkqjrhpn39wk42xmpl"
    }

For more information, see `Shared AWS Cloud Map namespaces <https://docs.aws.amazon.com/cloud-map/latest/dg/sharing-namespaces.html>`__ and `Deregistering an AWS Cloud Map service instance <https://docs.aws.amazon.com/cloud-map/latest/dg/deregistering-instances.html>`__ in the *AWS Cloud Map Developer Guide*.

