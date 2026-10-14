**To get the resource policy for a component**

The following ``get-component-policy`` example retrieves the resource policy that's applied to a component that the owner shared with another account. The ``policy`` field in the response contains the policy as a JSON text string. ::

    aws imagebuilder get-component-policy \
        --component-arn arn:aws:imagebuilder:us-west-2:123456789012:component/my-shared-component/1.0.0/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "policy": "{\"Version\": \"2012-10-17\", \"Statement\": [{\"Effect\": \"Allow\", \"Principal\": {\"AWS\": \"arn:aws:iam::123456789111:root\"}, \"Action\": [\"imagebuilder:GetComponent\", \"imagebuilder:ListComponents\"], \"Resource\": [\"arn:aws:imagebuilder:us-west-2:123456789012:component/my-shared-component/1.0.0/1\"]}]}"
    }

For more information, see `Share Image Builder resources with AWS RAM <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-shared-resources.html>`__ in the *EC2 Image Builder User Guide*.
