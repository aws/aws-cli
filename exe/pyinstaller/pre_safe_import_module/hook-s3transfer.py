# Since we've removed the custom importer, we don't need to add an alias module anymore
def pre_safe_import_module(api):
    # No need to add alias module since imports now use awscli.s3transfer directly
    pass
