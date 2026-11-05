**To describe Dedicated Host Reservations in your account**

The following ``describe-host-reservations`` example describes the Dedicated Host Reservations in your account. ::

    aws ec2 describe-host-reservations

Output::

    {
        "HostReservationSet": [
            {
                "Count": 1,
                "End": "2019-01-10T12:14:09Z",
                "HourlyPrice": "1.499",
                "InstanceFamily": "m4",
                "OfferingId": "hro-03f707bf363b6b324",
                "PaymentOption": "NoUpfront",
                "State": "active",
                "HostIdSet": [
                    "h-013abcd2a00cbd123"
                ],
                "Start": "2018-01-10T12:14:09Z",
                "HostReservationId": "hr-0d418a3a4ffc669ae",
                "UpfrontPrice": "0.000",
                "Duration": 31536000
            }
        ]
    }

For more information, see `Amazon EC2 Dedicated Host pricing and billing <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-billing.html#dedicated-host-reservations>`__ in the *Amazon EC2 User Guide*.
