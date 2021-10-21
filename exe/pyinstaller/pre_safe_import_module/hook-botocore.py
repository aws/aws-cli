def pre_safe_import_module(api):
    real_module_name = f'awscli.{api.module_name}'
    api.add_alias_module(real_module_name, api.module_name)
