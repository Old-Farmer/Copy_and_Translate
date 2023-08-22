import urllib.request
import os
from tqdm import tqdm

from selextrans.data_processing import configs, configs_file, LoadData
from selextrans.paths import AbsolutePath

configs = LoadData(configs_file)

# download language data files
tessdata_dir = AbsolutePath(configs["tessdata_dir"])
if not os.path.exists(tessdata_dir):
    os.makedirs(tessdata_dir)

url_base = "https://github.com/tesseract-ocr/tessdata/raw/4.00"
file_extension = ".traineddata"

languages = configs["languages_for_tesseract"]


def DownloadFileWithProgressBar(url, save_path):
    response = urllib.request.urlopen(url)
    file_size = int(response.info().get("Content-Length", 0))

    progress_bar = tqdm(total=file_size, unit="B", unit_scale=True, postfix=save_path)

    try:
        # download and update progress bar
        with open(save_path, "wb") as file:
            while True:
                buffer = response.read(8192)
                if not buffer:
                    break
                file.write(buffer)
                progress_bar.update(len(buffer))
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        print(str(e))

    progress_bar.close()


def DownloadFile(url, save_path):
    try:
        urllib.request.urlretrieve(url, save_path)
    except Exception as e:
        if os.path.exists(save_path):
            os.remove(save_path)
        print(str(e))


# check and download
for lang in languages:
    file_name = lang + file_extension
    save_path = tessdata_dir + "/" + file_name
    if os.path.exists(save_path):  # exist just skip
        continue

    url = url_base + "/" + file_name
    DownloadFileWithProgressBar(url, save_path)

print("Setup OK")
