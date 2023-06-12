import json

settings_file_name = 'ct_settings.json'

settings = dict()

def DumpData(file_name, data):
  with open(file_name, 'w') as file:
    json.dump(data, file, indent=4)

def LoadData(file_name):
  with open(file_name, 'r') as file:
    return json.load(file)

if __name__ == "__main__":
  pass

