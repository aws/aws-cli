**To set the instance affinity value for a specific stopped Dedicated host**

To modify the affinity of an instance so it always has affinity with the specified Dedicated host . 

Command::

  aws ec2 modify-instance-placement --instance-id=i-f0d45a40 --host-id h-029e7409a3350a31f

Output::

  { 
    "Return":  true
   }
