# Selextrans

![icon](./img/selextrans.png "icon")

It is an easy-to-use app which can translate selected text without copying manually.

## Python

This app is developed with **Python 3.10**.

## Platform Support

* **Linux (Debian/Ubuntu)**. If you use other Linux distributions, I suggest you to checkout the Dependencies carfully. The latter part of the document will only explain the use of `apt` for dependency configuration.
* **Windows**

## Quick Start

Here is a **quick start** for Linux usres who only use `pip` and `apt` to configure env. Run the following script, then you can jump to **How to Use**.

```shell
git clone https://github.com/Old-Farmer/Selextrans.git
cd Selextrans
./setup.sh # Set up before first running the app
./app.sh # run the app
```

## Dependencies

### Linux

* xclip
* tesseract ocr engine (**no data file need to be downloaded**)

```shell
sudo apt install xclip tesseract-ocr
```

### Windows

* tesseract ocr engine (**no data file need to be downloaded**). Check the website [Home · UB-Mannheim/tesseract Wiki · GitHub](https://github.com/UB-Mannheim/tesseract/wiki) and install Tesseract. Just Install it in the **default configure**, and choose a path to install it. Do not forget to set `"tesseract_cmd"` in `data/settings.json` which will be explained in **Settings** with details.

### Requirements for Python packages

* requests
* pyperclip
* pynput
* langid
* googletrans>=4.0.0rc1
* httpcore
* tkinter
* winreg **(For Windows)**
* pytesseract
* tqdm
* openai
* tiktoken
* pyqt5
* pyautogui

```shell
# For linux
sudo apt install python3-tk # For tkinter
pip install -r requirements_Linux.txt --upgrade
```

```powershell
# For Windows
pip install -r requirements_Windows.txt --upgrade
```

## How to Use

### Text translate

Select text, press `F2`, then translation results will be shown.

Or just type sth. into the input textbox, press `Enter`, then translation results will be shown.

![example.png](./img/example.png)

### Screenshot translate

Press `F4`, select a screen area, then translation results will be shown. Auto source language is not supported here.

**To select an area**, you need to press the left mouse button, drag the mouse to select the desired area, and finally release the button to complete the selection. You can press the right mouse button or `Esc` to cancel a selection.

### Other functions

* `F5` for refreshing

## Run and Setup

Directly run the `run.py`.

**Attention:**  if you **first** run the app, run `setup.py` first to **do some setups,** which will take some time.

## Settings

All Settings is in `data/settings.json`. Please **restart** the app if you change the file.

```json
{
    "https_proxy": "http://127.0.0.1:7890/",
    "request_url_for_baidu_api": "https://fanyi-api.baidu.com/api/trans/vip/translate",
    "private_key_for_baidu_api": "",
    "appid_for_baidu_api": "",
    "openai_api_key": "",
    "engine": "google",
    "mode": "dark",
    "text_translate_shortcut_key": "<f2>",
    "screenshot_translate_shortcut_key": "<f4>",
    "copy_key": "<ctrl>+c",
    "tesseract_cmd": "tesseract"
}
```

`"engine"` can be set as `"google"`, `"baidu_api"` or `"openai_api"`.

`"google"` engine (**default engine**) uses googletrans lib, so using it is totally free and no configuration is required. **Please ensure that you can access the Google Translate website.** Googletrans lib needs your network proxy setting if you have set it in your computer. This software can automatically detect you proxy setting. But if the automatic detection can't work for you computer, you can manually set `"https_proxy"` to specify the proxy. Leave it empty if you never set network proxy in your computer or you want automaitc detection to work.

`"baidu_api"` engine uses 百度通用文本翻译API (Baidu General Text Translation API), and requires `"private_key_for_baidu_api"`and `"appid_for_baidu_api"` to be set ( The corresponding website is [百度翻译开放平台](https://api.fanyi.baidu.com/doc/21)  ).

`"openai_api"` engine requires `"openai_api_key"` to be set. (The corresponding website is [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys)) `"openai_api"` engine is **not as fast as other engines**, so the app shows translation results **token by token**.

`"mode"` can be set as `"dark"` or `"light"`.

`"xx_shortcut_key"` specify shortcut key combinations for some functions. Key combinations are sequences of key identifiers separated by `"+"`. Key identifiers are either single characters representing a keyboard key, such as `"a"`, or special key names identified by names enclosed by brackets, such as `"<ctrl>"`. **You can set your own shortcut key combinations for convenience.**

`"copy_key"` is used for text translate to copy selected text to this app. The default setting `"<ctrl>+c"` can work for most softwares, except some softwares, e.g. command line programs. If you really want to use this app with specifc softwares, set `"copy_key"` as you want.

`"tesseract_cmd"` defines the command to start tesseract, which can be the executable file path or just the command `"tesseract"`. For Windows, if you do not set the environment variable for tesseract, set `"tesseract_cmd"` as the executable file `tesseract.exe` path. Use `/` or `\\` as seperators.

## Language Support

* Chinese (simplified) 简体中文
* Chinese (traditional) 繁體中文
* English
* French Français
* Russian Русскийязык
* Japanese 日本語
* Korean 한국어

## Customize languages

If you want to add other languages, Please follow the following steps:

1. Find the `data/configs.json` file.
2. Focus on `"languages"`, `"languages_for_google"`, `"languages_for_baidu_api"`, `"languages_for_tessertact"`. If you never use baidu api, you can ignore `"languages_for_baidu_api"`. The last three kv pairs are perfectly matching with the first one. For example, `"Chinese (Simplified)"` in  `"languages"` <=> `"zh-cn"` in `"languages_for_google"`.
3. What you should do is to add sth and to keep the match. Add a language name in `"languages"`, and then add the corresponding language code referenced by [Googletrans: Free and Unlimited Google translate API for Python — Googletrans 3.0.0 documentation](https://py-googletrans.readthedocs.io/en/latest/) in `"languages_for_google"` at the same index. Samely, if you want to use baidu api, add the corresponding language code referenced by [百度翻译开放平台](https://api.fanyi.baidu.com/doc/21) in `"languages_for_baidu_api"` at the same index.  Last, add the corresponding language code in `"languages_for_tessertact"` at the same index, and **download** the corresponding data file to `data/tessdata`, referenced by [Traineddata Files for Version 4.00 + | tessdoc](https://tesseract-ocr.github.io/tessdoc/Data-Files.html).
