def bug(issue=None):
    message = "A known bug."
    if issue is not None:
        message += " See issue #{issue}.".format(issue=issue)
    return message
