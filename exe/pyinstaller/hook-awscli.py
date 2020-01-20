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

imports_for_legacy_plugins = (
    hooks.collect_submodules('http') +
    hooks.collect_submodules('logging')
)

hiddenimports += imports_for_legacy_plugins

datas = hooks.collect_data_files('awscli')
