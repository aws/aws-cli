**To delete a queued purchase**

The following ``delete-queued-reserved-instances`` example deletes the specified Reserved Instance, which was queued for purchase. ::

    aws ec2 delete-queued-reserved-instances \
        --reserved-instances-ids a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "SuccessfulQueuedPurchaseDeletions": [
            {
                "ReservedInstancesId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ],
        "FailedQueuedPurchaseDeletions": []
    }

For more information, see `Cancel a queued purchase <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html#cancel-queued-purchase>`__ in the *Amazon EC2 User Guide*.
