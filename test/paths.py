import os

current_dir = os.path.dirname(__file__)
root_path = os.path.dirname(current_dir)


def AbsolutePath(related_path, prefix=root_path):
    return root_path + '/' + related_path
