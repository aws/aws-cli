**To get component policy details**

The following ``get-component-policy`` example lists the details of a component policy by specifying its ARN. ::

    aws imagebuilder get-component-policy \
        --component-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/2019.12.03/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "policy": "{ \"Version\": \"2012-10-17\", \"Statement\": [ { \"Effect\": \"Allow\", \"Principal\": { \"AWS\": [ \"123456789012\" ] }, \"Action\": [ \"imagebuilder:GetComponent\", \"imagebuilder:ListComponents\" ], \"Resource\": [ \"arn:aws:imagebuilder:us-west-2:123456789012:component/my-example-component/2019.12.03/1\" ] } ] }"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.