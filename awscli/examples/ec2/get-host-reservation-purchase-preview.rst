**To get a purchase preview for a Dedicated Host Reservation**

The following ``get-host-reservation-purchase-preview`` example provides a preview of the costs for a specified Dedicated Host Reservation for the specified Dedicated Host in your account. ::

    aws ec2 get-host-reservation-purchase-preview \
        --offering-id hro-03f707bf363b6b324 \
        --host-id-set h-013abcd2a00cbd123

Output::

    {
        "TotalHourlyPrice": "1.499",
        "Purchase": [
            {
                "HourlyPrice": "1.499",
                "InstanceFamily": "m4",
                "PaymentOption": "NoUpfront",
                "HostIdSet": [
                    "h-013abcd2a00cbd123"
                ],
                "UpfrontPrice": "0.000",
                "Duration": 31536000
            }
        ],
        "TotalUpfrontPrice": "0.000"
    }

For more information, see `Amazon EC2 Dedicated Host pricing and billing <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/dedicated-hosts-billing.html#dedicated-host-reservations>`__ in the *Amazon EC2 User Guide*.
