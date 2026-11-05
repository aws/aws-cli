**To turn off Resource Explorer in an AWS Region by deleting its index**

The following ``delete-index`` example deletes the specified Resource Explorer index in the AWS Region in which you make the request. ::

    aws resource-explorer-2 delete-index \
        --arn arn:aws:resource-explorer-2:us-west-2:123456789012:index/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --region us-west-2

Output::

    {
        "Arn": "arn:aws:resource-explorer-2:us-west-2:123456789012:index/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "State": "DELETING"
    }

For more information about deleting an index, see `Turning off Resource Explorer <https://docs.aws.amazon.com/resource-explorer/latest/userguide/manage-service-turn-off.html>`__ in the *AWS Resource Explorer Users Guide*.