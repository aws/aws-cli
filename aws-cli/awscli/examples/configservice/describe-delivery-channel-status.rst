**To get status information for the delivery channel**

The following ``describe-delivery-channel-status`` example returns the status of the delivery channel. ::

    aws configservice describe-delivery-channel-status

Output::

    {
        "DeliveryChannelsStatus": [
            {
                "configStreamDeliveryInfo": {
                    "lastStatusChangeTime": 1452193834.381,
                    "lastStatus": "SUCCESS"
                },
                "configHistoryDeliveryInfo": {
                    "lastSuccessfulTime": 1450317838.412,
                    "lastStatus": "SUCCESS",
                    "lastAttemptTime": 1450317838.412
                },
                "configSnapshotDeliveryInfo": {
                    "lastSuccessfulTime": 1452185597.094,
                    "lastStatus": "SUCCESS",
                    "lastAttemptTime": 1452185597.094
                },
                "name": "default"
            }
        ]
    }

For more information, see `Working with the Delivery Channel <https://docs.aws.amazon.com/config/latest/developerguide/manage-delivery-channel.html>`__ in the *AWS Config Developer Guide*.
