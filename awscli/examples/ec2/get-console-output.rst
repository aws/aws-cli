**To get the console output**

This example gets the console ouput for the specified Linux instance.

Command::

  aws ec2 get-console-output --instance-id i-1234567890abcdef0

Output::

  {
      "InstanceId": "i-1234567890abcdef0",
      "Timestamp": "2013-07-25T21:23:53.000Z",
      "Output": "..."
  }

**To get the latest console output**

This example gets the latest console output for the specified instance.

Command::

  aws ec2 get-console-output --instance-id i-1234567890abcdef0 --latest --output text


Output::

    i-1234567890abcdef0	[    0.000000] Command line: root=LABEL=/ console=tty1 console=ttyS0 selinux=0 nvme_core.io_timeout=4294967295
  [    0.000000] x86/fpu: Supporting XSAVE feature 0x001: 'x87 floating point registers'
  [    0.000000] x86/fpu: Supporting XSAVE feature 0x002: 'SSE registers'
  [    0.000000] x86/fpu: Supporting XSAVE feature 0x004: 'AVX registers'
  ...
  Cloud-init v. 0.7.6 finished at Wed, 09 May 2018 19:01:13 +0000. Datasource DataSourceEc2.  Up 21.50 seconds
  Amazon Linux AMI release 2018.03
  Kernel 4.14.26-46.32.amzn1.x86_64 on an x86_64
    2018-05-09T19:07:01.000Z