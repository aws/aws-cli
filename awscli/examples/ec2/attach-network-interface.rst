**To attach a network interface to an instance**

This example attaches the specified network interface to the specified instance.

Command::

  aws ec2 attach-network-interface --network-interface-id eni-e5aa89a3 --instance-id i-1234567890abcdef0 --device-index 1

Output::

  {
      "AttachmentId": "eni-attach-66c4350a"
  }