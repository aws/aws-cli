**To delete a queued purchase**

The following ``delete-queued-reserved-instances`` example deletes the specified Reserved Instance, which was queued for purchase. ::

    aws ec2 delete-queued-reserved-instances \
        --reserved-instances-ids af9f760e-6f91-4559-85f7-4980eexample

Output::

    {
        "SuccessfulQueuedPurchaseDeletions": [
            {
                "ReservedInstancesId": "af9f760e-6f91-4559-85f7-4980eexample"
            }
        ],
        "FailedQueuedPurchaseDeletions": []
    }

For more information, see `Cancel a queued purchase <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ri-market-concepts-buying.html#cancel-queued-purchase>`__ in the *Amazon EC2 User Guide*.
