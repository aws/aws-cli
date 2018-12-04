**To allocate a Dedicated host to your account**

This example allocates a single Dedicated host in a specific Availability Zone, onto which you can launch m3.medium instances, to your account. 

Command::

    aws ec2 allocate-hosts --instance-type m3.medium --availability-zone us-east-1b --quantity 1

Output::

  {
      "HostIds": [
      "h-029e7409a337631f"
      ]
  }


