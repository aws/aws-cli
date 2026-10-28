**To cancel Spot Instance requests**

The following ``cancel-spot-instance-requests`` example cancels a Spot Instance request. ::

    aws ec2 cancel-spot-instance-requests --spot-instance-request-ids sir-08b93456

Output::

    {
        "CancelledSpotInstanceRequests": [
            {
                "State": "cancelled",
                "SpotInstanceRequestId": "sir-08b93456"
            }
        ]
    }

