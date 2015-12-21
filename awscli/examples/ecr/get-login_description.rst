Log in to an Amazon ECR registry.

This command retrieves a token that is valid for a specified registry for 12
hours, and then it prints a ``docker login`` command with that authorization
token. You can execute the printed command to log in to your registry with
Docker. After you have logged in to an Amazon ECR registry with this command,
you can use the Docker CLI to push and pull images from that registry until the
token expires.

.. note::

    This command writes displays ``docker login`` commands to stdout with
    authentication credentials. Your credentials could be visible by other
    users on your system in a process list display or a command history. If you
    are not on a secure system, you should consider this risk and login
    interactively. For more information, see ``get-authorization-token``.
