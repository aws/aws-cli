**To describe the ID format for your resources**

This example describes the ID format for all resource types that support longer IDs. The output indicates that the ``instance``, ``reservation``, ``volume``, and ``snapshot`` resource types can be enabled or disabled for longer IDs. The ``reservation`` resource is already enabled. The ``Deadline`` field indicates the date (in UTC) at which you're automatically switched over to using longer IDs for that resource type. If a deadline is not yet available for the resource type, this value is not returned.

Command::

  aws ec2 describe-id-format

Output::

  {
    "Statuses": [
      {
        "Deadline": "2016-11-01T13:00:00.000Z",
        "UseLongIds": false,
        "Resource": "instance"
      },
      {
        "Deadline": "2016-11-01T13:00:00.000Z",
        "UseLongIds": true,
        "Resource": "reservation"
      },
      {
        "Deadline": "2016-11-01T13:00:00.000Z",
        "UseLongIds": false,
        "Resource": "volume"
      },
      {
        "Deadline": "2016-11-01T13:00:00.000Z",
        "UseLongIds": false,
        "Resource": "snapshot"
      }
    ]
  }