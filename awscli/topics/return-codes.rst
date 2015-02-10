:title: AWS CLI Return Codes
:description: Describes the various return codes of the AWS CLI
:category: General Topics, S3, Troubleshooting
:related command: s3, s3 cp, s3 sync, s3 mv, s3 rm

These are the following return codes returned at the end of execution
of a CLI command:

* ``0`` -- Command was successful. There were no errors thrown by either
  the CLI or by the service the request was made to.

* ``1`` -- Limited to ``s3`` commands, at least one or more s3 transfers
  failed for the command executed.

* ``2`` -- Limited to ``s3`` commands, at least one or more files marked
  for transfer were skipped during the transfer process. However, all
  other files marked for transfer were successfully transferred.
  Files that are skipped during the transfer process include:
  files that do not exist, files that are character special devices,
  block special device, FIFO's, or sockets, and files that the user cannot
  read from.

* ``255`` -- Command failed. There were errors thrown by either the CLI or
  by the service the request was made to.


To determine the return code of a command, run the following right after
running a CLI command. Note that this will work only on POSIX systems::

  $ echo $?


Output (if successful)::

  0
