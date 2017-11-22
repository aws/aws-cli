Configure temporary session credentials

The ``aws configure mfa`` command can be used to configure the MFA device to use (first time configuration), generate new or refresh existing temporary session credentials.

This command expects initial configuration for the cli to have been successfully completed (see ``aws configure help`` for more information).

On initial configuration, if one is not passed in via ``--serial-number``, the user will be asked to select from a list of existing MFA devices (if more than one exists).

On successful generation of new temporary credentials, the original credential values are preserved in corresponding configuration names suffixed by ``_saved`` within the shared credentials file (``~/.aws/credentials``).
