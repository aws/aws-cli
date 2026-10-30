**Example 1: To create a Capacity Reservation**

The following ``create-capacity-reservation`` example creates a capacity reservation in the ``us-west-2a`` Availability Zone, into which you can launch three ``t2.medium`` instances running a Linux/Unix operating system. By default, the capacity reservation is created with open instance matching criteria and no support for ephemeral storage, and it remains active until you manually cancel it. ::

    aws ec2 create-capacity-reservation \
        --availability-zone us-west-2a \
        --instance-type t2.medium \
        --instance-platform Linux/UNIX \
        --instance-count 3

Output::

    {
        "CapacityReservation": {
            "CapacityReservationId": "cr-1234abcd56EXAMPLE ",
            "EndDateType": "unlimited",
            "AvailabilityZone": "us-west-2a",
            "InstanceMatchCriteria": "open",
            "EphemeralStorage": false,
            "CreateDate": "2019-08-16T09:27:35.000Z",
            "AvailableInstanceCount": 3,
            "InstancePlatform": "Linux/UNIX",
            "TotalInstanceCount": 3,
            "State": "active",
            "Tenancy": "default",
            "EbsOptimized": false,
            "InstanceType": "t2.medium"
        }
    }

**Example 2: To create a Capacity Reservation that automatically ends at a specified date/time**

The following ``create-capacity-reservation`` example creates a capacity reservation in the ``us-west-2a`` Availability Zone, into which you can launch three ``m5.large`` instances running a Linux/Unix operating system. This capacity reservation automatically ends on 08/31/2019 at 23:59:59. ::

    aws ec2 create-capacity-reservation \
        --availability-zone us-west-2a \
        --instance-type m5.large \
        --instance-platform Linux/UNIX \
        --instance-count 3 \
        --end-date-type limited \
        --end-date 2019-08-31T23:59:59Z

Output::

    {
        "CapacityReservation": {
            "CapacityReservationId": "cr-1234abcd56EXAMPLE ",
            "EndDateType": "limited",
            "AvailabilityZone": "us-west-2a",
            "EndDate": "2019-08-31T23:59:59.000Z",
            "InstanceMatchCriteria": "open",
            "EphemeralStorage": false,
            "CreateDate": "2019-08-16T10:15:53.000Z",
            "AvailableInstanceCount": 3,
            "InstancePlatform": "Linux/UNIX",
            "TotalInstanceCount": 3,
            "State": "active",
            "Tenancy": "default",
            "EbsOptimized": false,
            "InstanceType": "m5.large"
        }
    }

**Example 3: To create a Capacity Reservation that accepts only targeted instance launches**

The following ``create-capacity-reservation`` example creates a capacity reservation that accepts only targeted instance launches. ::

    aws ec2 create-capacity-reservation \
        --availability-zone us-west-2a \
        --instance-type m5.large \
        --instance-platform Linux/UNIX \
        --instance-count 3 \
        --instance-match-criteria targeted

Output::

    {
        "CapacityReservation": {
            "CapacityReservationId": "cr-1234abcd56EXAMPLE ",
            "EndDateType": "unlimited",
            "AvailabilityZone": "us-west-2a",
            "InstanceMatchCriteria": "targeted",
            "EphemeralStorage": false,
            "CreateDate": "2019-08-16T10:21:57.000Z",
            "AvailableInstanceCount": 3,
            "InstancePlatform": "Linux/UNIX",
            "TotalInstanceCount": 3,
            "State": "active",
            "Tenancy": "default",
            "EbsOptimized": false,
            "InstanceType": "m5.large"
        }
    }

For more information, see `Create a Capacity Reservation <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/capacity-reservations-using.html>`__ in the *Amazon EC2 User Guide*.
