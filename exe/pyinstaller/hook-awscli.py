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

datas = hooks.collect_data_files('awscli')
# prompt_toolkit uses its own metadata to determine
# its version. So we need to bundle the package
# metadata to avoid runtime errors.
# https://github.com/aws/aws-cli/issues/9453
datas += hooks.copy_metadata('prompt_toolkit')
