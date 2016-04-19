**To set the instance affinity value for a specific stopped Dedicated Host**

To modify the affinity of an instance so it always has affinity with the specified Dedicated Host . 

Command::

  aws ec2 modify-instance-placement --instance-id=i-1234567890abcdef0 --host-id h-029e7409a3350a31f

Output::

  { 
    "Return":  true
   }
