import json
from selextrans.paths import AbsolutePath

configs_file = AbsolutePath('data/configs.json')
settings_file = AbsolutePath('data/settings.json')

configs = dict()
settings = dict()


def DumpData(file_name, data):
    with open(file_name, 'w') as file:
        json.dump(data, file, indent=4)


def LoadData(file_name):
    with open(file_name, 'r') as file:
        return json.load(file)

