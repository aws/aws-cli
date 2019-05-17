**To list all active Session Manager sessions**

This example retrieves a list of the active sessions created most recently (both connected and disconnected sessions) over the past 30 days that were started by a particular user.

Command::

  aws ssm describe-sessions --state "Active" --filters "key=Owner,value=arn:aws:sts::123456789012:assumed-role/Administrator/Matt"

Output::

  {
    "Sessions": [
        {
            "SessionId": "Matt-07a16060613c408b5",
            "Target": "i-1234567890abcdef0",
            "Status": "Connected",
            "StartDate": 1550676938.352,
            "Owner": "arn:aws:sts::123456789012:assumed-role/Administrator/Matt",
            "OutputUrl": {}
        },
        {
            "SessionId": "Matt-01edf534b8b56e8eb",
            "Target": "i-9876543210abcdef0",
            "Status": "Connected",
            "StartDate": 1550676842.194,
            "Owner": "arn:aws:sts::123456789012:assumed-role/Administrator/Matt",
            "OutputUrl": {}
        }
    ]
  }

**To list all terminated Session Manager sessions**

This example retrieves a list of the most recently terminated sessions from the past 30 days for all users.

Command::

  aws ssm describe-sessions --state "History"

Output::

  {
    "Sessions": [
        {
            "SessionId": "Dan-0022b1eb2b0d9e3bd",
            "Target": "i-1234567890abcdef0",
            "Status": "Terminated",
            "StartDate": 1550520701.256,
            "EndDate": 1550521931.563,
            "Owner": "arn:aws:sts::123456789012:assumed-role/Administrator/Dan"
        },
        {
            "SessionId": "Erik-0db53f487931ed9d4",
            "Target": "i-9876543210abcdef0",
            "Status": "Terminated",
            "StartDate": 1550161369.149,
            "EndDate": 1550162580.329,
            "Owner": "arn:aws:sts::123456789012:assumed-role/Administrator/Erik"
        },
		...
    ],
    "NextToken": "--token string truncated--"
  }
  