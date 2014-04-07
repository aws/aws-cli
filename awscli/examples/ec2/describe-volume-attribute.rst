**To describe a volume attribute**

This example command describes the ``autoEnableIo`` attribute of the volume with the ID ``vol-2725bc51``.

Command::

  aws ec2 describe-volume-attribute --volume-id vol-2725bc51 --attribute autoEnableIO

Output::

   {
       "AutoEnableIO": {
           "Value": false
       },
       "ProductCodes": [],
       "VolumeId": "vol-2725bc51"
   }