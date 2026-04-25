import os

from PyInstaller.utils import hooks

hiddenimports = [
    'docutils',
    'urllib',
    'httplib',
    'html.parser',
    'configparser',
    'xml.etree',
    'pipes',
    'colorama',
    'awscli.handlers',
]

imports_for_legacy_plugins = hooks.collect_submodules(
    'http'
) + hooks.collect_submodules('logging')
hiddenimports += imports_for_legacy_plugins

alias_packages_plugins = hooks.collect_submodules(
    'awscli.botocore'
) + hooks.collect_submodules('awscli.s3transfer')
hiddenimports += alias_packages_plugins


# Completion model files are only used at build time to generate the
# ac.index SQLite database. They are not needed at runtime and can be
# excluded to reduce the size of the PyInstaller distribution.
EXCLUDED_DATA_FILE_BASENAMES = {
    'completions-1.json',
    'completions-1.sdk-extras.json',
}


datas = [
    (src, dest)
    for src, dest in hooks.collect_data_files('awscli')
    if os.path.basename(src) not in EXCLUDED_DATA_FILE_BASENAMES
]


# prompt_toolkit uses its own metadata to determine
# its version. So we need to bundle the package
# metadata to avoid runtime errors.
# https://github.com/aws/aws-cli/issues/9453
datas += hooks.copy_metadata('prompt_toolkit')
