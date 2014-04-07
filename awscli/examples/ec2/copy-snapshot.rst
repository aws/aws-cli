**To copy a snapshot**

This example command copies a snapshot with the snapshot ID of ``snap-1234abcd`` from the ``us-west-2`` region to the ``us-east-1`` region and adds a short description to identify the snapshot.

Command::

  aws --region us-east-1 ec2 copy-snapshot --source-region us-west-2 --source-snapshot-id snap-1234abcd --description "This is my copied snapshot."

Output::

   {
       "SnapshotId": "snap-2345bcde"
   }