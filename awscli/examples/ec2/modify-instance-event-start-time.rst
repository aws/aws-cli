**To modify the event start time for an instance**

The following ``modify-instance-event-start-time`` example modifies the event start time for the specified instance. Specify the event ID by using the ``--instance-event-id`` parameter. Specify the new date and time by using the ``--not-before`` parameter. ::

    aws ec2 modify-instance-event-start-time \
        --instance-id i-1234567890abcdef0 \
        --instance-event-id instance-event-0abcdef1234567890 \
        --not-before 2019-03-25T10:00:00.000

Output::

    {
        "Event": {
            "InstanceEventId": "instance-event-0abcdef1234567890",
            "Code": "system-reboot",
            "Description": "scheduled reboot",
            "NotAfter": "2019-03-25T12:00:00.000Z",
            "NotBefore": "2019-03-25T10:00:00.000Z",
            "NotBeforeDeadline": "2019-04-22T21:00:00.000Z"
        }
    }

For more information, see `Reschedule a scheduled event for an EC2 instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/reschedule-event.html>`__ in the *Amazon EC2 User Guide*.
