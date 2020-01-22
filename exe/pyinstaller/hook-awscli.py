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
    # NOTE: This can be removed once this hidden import issue related to
    # setuptools and PyInstaller is resolved:
    # https://github.com/pypa/setuptools/issues/1963
    'pkg_resources.py2_warn'
]

imports_for_legacy_plugins = (
    hooks.collect_submodules('http') +
    hooks.collect_submodules('logging')
)

hiddenimports += imports_for_legacy_plugins

datas = hooks.collect_data_files('awscli')
