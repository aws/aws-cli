**To cancel Spot Instance requests**

The following ``cancel-spot-instance-requests`` example cancels a Spot Instance request. ::

    aws ec2 cancel-spot-instance-requests \
        --spot-instance-request-ids sir-08b93456

Output::

    {
        "CancelledSpotInstanceRequests": [
            {
                "State": "cancelled",
                "SpotInstanceRequestId": "sir-08b93456"
            }
        ]
    }

For more information, see `Cancel a Spot Instance request <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances-cancel.html>`__ in the *Amazon EC2 User Guide*.
