import os
import platform
import hashlib
import requests
import secrets
import pyperclip
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from pynput import keyboard as kb
# import asyncio
# import httpx
import time
import langid
# import keyboard as kb
# import re
from googletrans import Translator  # must be >=4.0.0rc1
from httpcore import SyncHTTPProxy
from urllib.parse import urlparse

from data_processing import DumpData, LoadData, configs, configs_file, settings, settings_file

import subprocess
import pytesseract
from PIL import ImageGrab

# golbal var
languages = []
src_languages = []
dest_languages = []
languages_for_tesseract = []

system_name = platform.system()

tessdata_dir_config = ''


def LoadConfigs():
    global configs, languages, src_languages, dest_languages, languages_for_tesseract, tessdata_dir_config

    configs = LoadData(configs_file)
    languages = configs['languages']
    src_languages = languages + ['auto']
    dest_languages = languages
    languages_for_tesseract = configs['languages_for_tesseract']

    # customize language data loc
    # pytesseract.pytesseract.tesseract_cmd = 'tesseract'
    tessdata_dir_config = '--tessdata-dir ' + configs['tessdata_dir']


def SaveConfigs():
    DumpData(configs_file, configs)


def LoadSettings():
    global settings
    settings = LoadData(settings_file)


def SaveSettings():
    DumpData(settings_file, settings)


# directly load some data here
LoadConfigs()
LoadSettings()


def PrintSceenToClipboard():
    '''
    Using tools for printscreen
    Windows & Macos haven't been tested yet
    '''
    system_name = platform.system()
    if system_name == 'Linux':  # linux
        try:
            subprocess.run(['gnome-screenshot', '-c', '-a'], check=True)
            return 1
        except subprocess.CalledProcessError:
            return 0
    elif system_name == 'Windows':  # Windows
        controller = kb.Controller()
        controller.press(kb.Key.shift)
        controller.press(kb.Key.cmd)
        controller.press('s')
        controller.release(kb.Key.shift)
        controller.release(kb.Key.cmd)
        controller.release('s')
        return 1
    elif system_name == 'Darwin':  # Macos
        try:
            subprocess.run(['screencapture', '-i', '-s'], check=True)
            return 1
        except subprocess.CalledProcessError:
            return 0
    else:
        return 0


def ProcessText(text):
    '''
    Mostly for PDF
    '''
    lang, _ = langid.classify(text)
    if lang in ['zh', 'ja']:  # Chinese, Japanese... do not need space to sep words
        return text.replace('\r', '').replace('\n', '').replace('\f', '')
    else:
        # /n -> space, '  ' -> ' '
        return text.replace('\r', '').replace('\n', ' ').replace('\f', '')


class BaiduAPITranslator:
    request_url_ = settings['request_url_for_baidu_api']
    languages_for_baidu_api_ = configs['languages_for_baidu_api']

    def __init__(self, appid, private_key):
        self.appid_ = appid
        self.private_key_ = private_key

    def Translate(self, src_text, src_language='auto', dest_language='en'):
        def Md5Encrypt(input_string):
            md5_hash = hashlib.md5()
            md5_hash.update(input_string.encode('utf-8'))
            encrypted_string = md5_hash.hexdigest()
            return encrypted_string

        def GenerateSalt(length=16):
            salt = secrets.token_hex(length // 2)
            return salt

        if self.appid_ == '':
            return '[Please offer appid and private key]'

        params = {
            'q': src_text,
            'from': src_language,
            'to': dest_language,
            'appid': self.appid_,
            'salt': GenerateSalt(),
            'sign': ''
        }

        params['sign'] = Md5Encrypt(params['appid']
                                    + params['q'] + params['salt'] + self.private_key_)

        # async with httpx.AsyncClient() as client:
        #   r = await client.get(request_url_, params=params)

        r = requests.get(BaiduAPITranslator.request_url_, params=params)

        if r.status_code != 200:
            return 0, 'Error happend, try again!'
        else:
            response = r.json()
            if response.get('trans_result') is not None:
                result = response['trans_result']
                # return 1, 'src: ' + result[0]['src'] + '\n' + 'translation: '+ result[0]['dst']
                return 1, result[0]['dst']
            else:
                return response['error_code'], '[Error: ' + response['error_msg'] + ']'

    def TranslateWrapper(self, src_text, src_lang_index, dest_lang_index):
        src_lang = 'auto' if src_lang_index == len(
            src_languages) - 1 else BaiduAPITranslator.languages_for_baidu_api_[src_lang_index]
        return self.Translate(
            src_text, src_language=src_lang, dest_language=BaiduAPITranslator.languages_for_baidu_api_[dest_lang_index])


class GoogleTranslator:
    '''
    '''
    languages_for_google_ = configs['languages_for_google']

    def __init__(self):
        if system_name == 'Linux' or system_name == 'Darwin':  # linux or mac
            all_proxy = os.environ.get('all_proxy')
            if all_proxy and urlparse(all_proxy).scheme == 'socks':
                if os.environ.get('http_proxy'):
                    # socks scheme is not supported by httpx library, so we just use http_proxy
                    os.environ['all_proxy'] = os.environ['http_proxy']
                else:
                    print('No http_proxy is set, but all_proxy is set')
                    exit(0)
            self.google_translator = Translator()
        elif system_name == 'Windows':  # windows
            import winreg
            INTERNET_SETTINGS = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                               r'Software\Microsoft\Windows\CurrentVersion\Internet Settings')

            def GetProxySettings():
                try:
                    proxy_enabled = winreg.QueryValueEx(
                        INTERNET_SETTINGS, 'ProxyEnable')[0]
                    if proxy_enabled == 1:
                        proxy_server = winreg.QueryValueEx(
                            INTERNET_SETTINGS, 'ProxyServer')[0]
                        return proxy_server
                    else:
                        return None
                except FileNotFoundError:
                    return None

            proxy = GetProxySettings()
            if proxy:
                ip, port = proxy.split(':')
                self.google_translator = Translator(proxies={'https': SyncHTTPProxy(
                    (b'http', ip.encode(), int(port), b''))})  # if can not get proxy from env var, set the proxy manually
            else:
                self.google_translator = Translator()

    def Translate(self, src_text, src_language='auto', dest_language='en'):
        try:
            r = self.google_translator.translate(
                src_text, src=src_language, dest=dest_language)
            return 1, r.text
        except Exception as e:
            # raise e
            return 0, '[Error: ' + str(e) + ']'

    def TranslateWrapper(self, src_text, src_lang_index, dest_lang_index):
        src_lang = 'auto' if src_lang_index == len(
            src_languages) - 1 else GoogleTranslator.languages_for_google_[src_lang_index]
        return self.Translate(
            src_text, src_language=src_lang, dest_language=GoogleTranslator.languages_for_google_[dest_lang_index])


class Gui:
    def __init__(self):

        # init translator
        engine = settings['engine']
        if engine == 'google':
            self.translator_ = GoogleTranslator()
        elif engine == 'baidu_api':
            self.translator_ = BaiduAPITranslator(
                settings['appid'], settings['private_key'])
        else:
            print('Please choose a translation engine')
            exit(0)

        # init gui
        self.window_ = tk.Tk()
        self.window_.title('Copy and Translate')
        self.window_.attributes("-topmost", True)

        global_font = tkfont.Font(size=15)
        self.window_.option_add('*Font', global_font)

        self.src_lang_combox_ = ttk.Combobox(
            self.window_, values=src_languages)
        self.inputText_ = tk.Text(self.window_, height=18, width=30)
        self.dest_lang_combox_ = ttk.Combobox(
            self.window_, values=dest_languages)
        self.outputText_ = tk.Text(
            self.window_, height=18, width=30)

        if settings['mode'] == 'dark':
            self.inputText_.configure(background='#292421', foreground='white')
            self.outputText_.configure(
                background='#292421', foreground='white')
            # still have some problem of the TCombobox color
            ttk.Style().configure('TCombobox', fieldbackground='#292421', foreground='white')
            self.window_.option_add('*TCombobox*Foreground', 'white')
            self.window_.option_add('*TCombobox*Background', '#292421')

        self.src_lang_combox_.grid(row=0, column=0, sticky='ew')
        self.inputText_.grid(row=1, column=0, sticky=tk.NSEW)
        self.dest_lang_combox_.grid(row=2, column=0, sticky='ew')
        self.outputText_.grid(row=3, column=0, sticky=tk.NSEW)

        # set weight
        self.window_.columnconfigure(0, weight=1)
        self.window_.rowconfigure(1, weight=1)
        self.window_.rowconfigure(3, weight=1)

        self.src_lang_combox_.current(len(src_languages) - 1)
        self.dest_lang_combox_.current(0)

        self.kbController_ = kb.Controller()

        self.listener_ = kb.Listener(on_press=self.OnPress)
        self.listener_.start()
        # self.listener_.join()

        self.inputText_.bind('<Return>', self.DoTrans)
        # self.src_lang_combox_.bind(
        #     '<<ComboboxSelected>>', self.HandleSrcLanguageSelect)
        # self.dest_lang_combox_.bind(
        #     '<<ComboboxSelected>>', self.HandleDestLanguageSelect)

        self.window_.mainloop()

    # def HandleSrcLanguageSelect(self, event):
    #     global src_lang_index
    #     src_lang_index = self.src_lang_combox_.current()

    # def HandleDestLanguageSelect(self, event):
    #     global dest_lang_index
    #     dest_lang_index = self.dest_lang_combox_.current()

    def OnPress(self, key):
        if key == kb.Key.f2:
            pre_content = pyperclip.paste()

            # with self.kbController_.pressed(kb.Key.ctrl):
            #   self.kbController_.press('c')
            self.kbController_.press(kb.Key.ctrl)
            self.kbController_.press('c')
            self.kbController_.release('c')
            self.kbController_.release(kb.Key.ctrl)

            # sleep here so that os can have time to copy content to the clipboard
            time.sleep(0.1)
            content = pyperclip.paste()
            pyperclip.copy(pre_content)  # recover
            self.inputText_.delete("1.0", tk.END)
            self.inputText_.insert(tk.END, content)

            self.DoTrans()

        elif key == kb.Key.f4:  # print sreen then ocr then translate
            pre_content = pyperclip.paste()
            result = PrintSceenToClipboard()
            if result == 0:
                self.inputText_.delete("1.0", tk.END)
                self.outputText_.delete("1.0", tk.END)
                self.outputText_.insert(tk.END, "[Print screen error]")
            else:
                img = ImageGrab.grabclipboard()
                src_lang_index = self.src_lang_combox_.current()
                if src_lang_index == len(src_languages) - 1:
                    self.inputText_.delete("1.0", tk.END)
                    self.outputText_.delete("1.0", tk.END)
                    self.outputText_.insert(
                        tk.END, "[Please choose a specific language for ocr]")
                    return
                content = pytesseract.image_to_string(
                    image=img, lang=languages_for_tesseract[src_lang_index], config=tessdata_dir_config)
                pyperclip.copy(pre_content)  # recover
                self.inputText_.delete("1.0", tk.END)
                self.inputText_.insert(tk.END, content)

                self.DoTrans()

    def DoTrans(self, event=None):
        content = self.inputText_.get('1.0', tk.END)
        # print(content)
        if content == '':
            return

        # trans = BaiduTranslate(content.replace('\n', '\\n'), 'en')[1].replace('\\', '\n') # baidu api has some problems with '\n'

        content = ProcessText(content)
        # print(content)
        self.inputText_.delete("1.0", tk.END)
        self.inputText_.insert(tk.END, content)

        self.outputText_.delete("1.0", tk.END)
        self.outputText_.insert(tk.END, "[Waiting for response...]")

        src_lang_index = self.src_lang_combox_.current()
        dest_lang_index = self.dest_lang_combox_.current()

        _, trans = self.translator_.TranslateWrapper(
            content, src_lang_index, dest_lang_index)

        self.outputText_.delete("1.0", tk.END)
        self.outputText_.insert(tk.END, trans)


if __name__ == '__main__':
    gui = Gui()
