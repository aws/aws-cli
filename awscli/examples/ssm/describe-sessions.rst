**To list all active Session Manager sessions**

This example retrieves a list of the most recently created active sessions (both connected and disconnected) sessions from the past 30 days that were started by a particular user. 

Command::

  aws ssm describe-sessions --state "Active" --max-results 25 --filters "key=Owner, value=arn:aws:iam::123456789012:user/Bob” 
  
Output::

  {
    "Sessions": [
        {
            "SessionId": "Bob-0cd1b1a98fEXAMPLE",
            "Target": "i-01d8e37ef8EXAMPLE",
            "Status": "Connected",
            "StartDate": 1541546231.193,
            "Owner": "aws:iam::123456789012:user/Bob",
            "OutputUrl": {}
        },
        {
            "SessionId": "tw-marbak-0d24bd8cc041095cd",
            "Target": "i-37ef801d8eEXAMPLE",
            "Status": "Connected",
            "StartDate": 1541545487.73,
            "DocumentName": "SSM-SessionManagerRunShell",
            "Owner": "aws:iam::123456789012:user/Bob",
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
            "SessionId": "Bob-05c56a28bdEXAMPLE",
            "Target": "i-0de68d8bd2EXAMPLE",
            "Status": "Terminated",
            "StartDate": 1541449551.82,
            "EndDate": 1541451079.541,
            "Owner": "arn:aws:iam::123456789012:user/Bob"
        },
        {
            "SessionId": "Jane-004800a5f0EXAMPLE",
            "Target": "i-d8bd20de68EXAMPLE",
            "Status": "Terminated",
            "StartDate": 1541449401.316,
            "EndDate": 1541451613.428,
            "Owner": "arn:aws:iam::123456789012:user/Jane"
        },
        {
            "SessionId": "Bob-0d00ec80d0EXAMPLE",
            "Target": "i-0de68d8bd2EXAMPLE",
            "Status": "Terminated",
            "StartDate": 1541448657.394,
            "EndDate": 1541450094.448,
            "Owner": "arn:aws:iam::123456789012:user/Bob"
        }
	]
}