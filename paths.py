import os
import platform

root_path = os.path.dirname(__file__)
# to Posix style
if platform.system() == "Windows":
    root_path = root_path.replace("\\", "/")


def AbsolutePath(related_path, prefix=root_path):
    return prefix + "/" + related_path