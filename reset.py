#!/bin/python3

import shutil
from paths import AbsolutePath

shutil.copy(AbsolutePath( "./data/settings_backup.json"), AbsolutePath("./data/settings.json"))
shutil.copy(AbsolutePath( "./data/configs_backup.json"), AbsolutePath("./data/configs.json"))
