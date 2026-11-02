**To get image policy details**

The following ``get-image-policy`` example lists the details of an image policy by specifying its ARN. ::

    aws imagebuilder get-image-policy \
        --image-arn arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-image/2019.12.03/1

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "policy": "{ \"Version\": \"2012-10-17\", \"Statement\": [ { \"Effect\": \"Allow\", \"Principal\": { \"AWS\": [ \"123456789012\" ] }, \"Action\": [ \"imagebuilder:GetImage\", \"imagebuilder:ListImages\" ], \"Resource\": [ \"arn:aws:imagebuilder:us-west-2:123456789012:image/my-example-image/2019.12.03/1\" ] } ] }"
    }

For more information, see `Manage custom image creation in Image Builder through a repeatable pipeline process <https://docs.aws.amazon.com/imagebuilder/latest/userguide/manage-pipelines.html>`__ in the *EC2 Image Builder Users Guide*.
