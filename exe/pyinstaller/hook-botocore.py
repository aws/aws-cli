#from PyInstaller.hooks.hookutils import collect_data_files
from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ['configparser', 'html.parser', 'markupbase', 'pipes', 'six']
datas = collect_data_files('botocore')
