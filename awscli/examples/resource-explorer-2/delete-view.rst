**To delete a Resource Explorer view**

The following ``delete-view`` example deletes a view specified by its ARN. ::

    aws resource-explorer-2 delete-view \
        --view-arn arn:aws:resource-explorer-2:us-west-2:123456789012:view/EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ViewArn": "arn:aws:resource-explorer-2:us-west-2:123456789012:view/EC2-Only-View/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Deleting views in Resource Explorer <https://docs.aws.amazon.com/resource-explorer/latest/userguide/configure-views-delete.html>`__ in the *AWS Resource Explorer Users Guide*.