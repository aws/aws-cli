**To modify an endpoint**

This example modifies endpoint vpce-1a2b3c4d by associating route table rtb-aaa222bb with the endpoint, and resetting the policy document.

Command::

  aws ec2 modify-vpc-endpoint --vpc-endpoint-id vpce-1a2b3c4d --add-route-table-ids rtb-aaa222bb --reset-policy

Output::

  {
    "Return": true
  }