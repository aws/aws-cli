:title: AWS CLI Return Codes
:description: Describes the various return codes of the AWS CLI
:category: General
:related command: s3, s3 cp, s3 sync, s3 mv, s3 rm

These are the following return codes returned at the end of execution
of a CLI command:

* ``0`` -- The service responded with an HTTP response status code of 200 and there 
  were no errors from either the CLI or the service the request was made to.

* ``1`` -- Limited to ``s3`` commands, at least one or more s3 transfers
  failed for the command executed.

* ``2`` -- The meaning of this return code depends on the command being run.

  The primary meaning is that the command entered on the command
  line failed to be parsed. Parsing failures can be caused by,
  but are not limited to, missing any required subcommands or arguments
  or using any unknown commands or arguments.
  Note that this return code meaning is applicable to all CLI commands.

  The other meaning is only applicable to ``s3`` commands.
  It can mean at least one or more files marked
  for transfer were skipped during the transfer process. However, all
  other files marked for transfer were successfully transferred.
  Files that are skipped during the transfer process include:
  files that do not exist, files that are character special devices,
  block special device, FIFO's, or sockets, and files that the user cannot
  read from.

* ``130`` -- The process received a SIGINT (Ctrl-C).

* ``255`` -- Command failed. There were errors from either the CLI or 
  the service the request was made to.


To determine the return code of a command, run the following right after
running a CLI command. Note that this will work only on POSIX systems::

  $ echo $?


Output (if successful)::

  0

On Windows PowerShell, the return code can be determined by running::

  > echo $lastexitcode

Output (if successful)::

  0


On Windows Command Prompt, the return code can be determined by running::

  > echo %errorlevel%

Output (if successful)::

  0
