import os
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

from data_processing import DumpData, LoadData, settings, settings_file_name

# golbal var
kRequestURL = ''
private_key = ''
appid = ''
engine = ''
languages = []
src_languages = []
dest_languages = []
src_lang_index = 0
dest_lang_index = 0
languages_for_google = []  # mapping to the languages
languages_for_baidu_api = []
# lang_pair_prefer = ['zh-cn', 'en']
# dest_lang_prefer = 'zh-cn'


def LoadSettings():
    global settings, kRequestURL, appid, engine, languages, src_languages, dest_languages, src_lang_index, dest_lang_index, languages_for_google, languages_for_baidu_api
    settings = LoadData(settings_file_name)
    kRequestURL = settings['request_url']
    appid = settings['appid']
    engine = settings['engine']
    languages = settings['languages']
    src_languages = languages + ['auto']
    dest_languages = languages
    src_lang_index = settings['src_lang_index']
    dest_lang_index = settings['dest_lang_index']
    languages_for_google = settings['languages_for_google']
    languages_for_baidu_api = settings['languages_for_baidu_api']


def SaveSettings():
    DumpData(settings_file_name, settings)
    

def ProcessText(text):
    '''
    Mostly for PDF
    '''
    lang, _ = langid.classify(text)
    if lang in ['zh', 'ja']: # Chinese, Japanese... do not need space to sep words
        return text.replace('\r', '').replace('\n', '')
    else:
        return text.replace('\r', ' ').replace('\n', '') # /r -> space


def Md5Encrypt(input_string):
    md5_hash = hashlib.md5()
    md5_hash.update(input_string.encode('utf-8'))
    encrypted_string = md5_hash.hexdigest()
    return encrypted_string


def GenerateSalt(length=16):
    salt = secrets.token_hex(length // 2)
    return salt


def BaiduTranslate(src_text, src_language='auto', dest_language='en'):
    if appid == '':
        return '[Please offer appid and private key]'

    params = {
        'q': src_text,
        'from': src_language,
        'to': dest_language,
        'appid': appid,
        'salt': GenerateSalt(),
        'sign': ''
    }

    params['sign'] = Md5Encrypt(params['appid']
                                + params['q'] + params['salt'] + private_key)

    # async with httpx.AsyncClient() as client:
    #   r = await client.get(kRequestURL, params=params)

    r = requests.get(kRequestURL, params=params)

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


if os.name == 'posix':  # linux or mac
    all_proxy = os.environ.get('all_proxy')
    if all_proxy and urlparse(all_proxy).scheme == 'socks':
        if os.environ.get('http_proxy'):
            # socks scheme is not supported by httpx library, so we just use http_proxy
            os.environ['all_proxy'] = os.environ['http_proxy']
        else:
            print('No http_proxy is set, but all_proxy is set')
            exit(0)
    google_translator = Translator()
elif os.name == 'nt':  # windows
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
        google_translator = Translator(proxies={'https': SyncHTTPProxy(
            (b'http', ip.encode(), int(port), b''))})  # if can not get proxy from env var, set the proxy manually
    else:
        google_translator = Translator()


def GoogleTranslate(src_text, src_language='auto', dest_language='en'):
    try:
        r = google_translator.translate(
            src_text, src=src_language, dest=dest_language)
        return 1, r.text
    except Exception as e:
        # raise e
        return 0, '[Error: ' + str(e) + ']'


def Cmd():
    while True:
        input_str = input('>>>')

        if input_str == 's':
            content = pyperclip.paste()
            print(BaiduTranslate(content)[1])
        elif input_str == 'q':
            break
        else:
            print('Try again!')


class Gui:
    def __init__(self):
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

        self.src_lang_combox_.grid(row=0, column=0, sticky='ew')
        self.inputText_.grid(row=1, column=0, sticky=tk.NSEW)
        self.dest_lang_combox_.grid(row=2, column=0, sticky='ew')
        self.outputText_.grid(row=3, column=0, sticky=tk.NSEW)

        # set weight
        self.window_.columnconfigure(0, weight=1)
        self.window_.rowconfigure(1, weight=1)
        self.window_.rowconfigure(3, weight=1)

        self.src_lang_combox_.current(src_lang_index)
        self.dest_lang_combox_.current(dest_lang_index)

        self.kbController_ = kb.Controller()

        self.listener_ = kb.Listener(on_press=self.OnPress)
        self.listener_.start()
        # self.listener_.join()

        self.inputText_.bind('<Return>', self.DoTrans)
        self.src_lang_combox_.bind(
            '<<ComboboxSelected>>', self.HandleSrcLanguageSelect)
        self.dest_lang_combox_.bind(
            '<<ComboboxSelected>>', self.HandleDestLanguageSelect)

        self.window_.mainloop()

    def HandleSrcLanguageSelect(self, event):
        global src_lang_index
        src_lang_index = self.src_lang_combox_.current()
        settings['src_lang_index'] = src_lang_index
        SaveSettings()

    def HandleDestLanguageSelect(self, event):
        global dest_lang_index
        dest_lang_index = self.dest_lang_combox_.current()
        settings['dest_lang_index'] = dest_lang_index
        SaveSettings()

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

        # src_lang_index = self.src_lang_combox_.current()
        # dest_lang_index = self.dest_lang_combox_.current()

        # if src_lang == 'auto':
        #     if dest_lang == 'auto':
        #         src_lang = google_translator.detect(content).lang
        #         print(src_lang)
        #         if src_lang == lang_pair_prefer[0]:
        #             dest_lang = lang_pair_prefer[1]
        #         elif src_lang == lang_pair_prefer[1]:
        #             dest_lang = lang_pair_prefer[0]
        #         else:
        #             dest_lang = dest_lang_prefer
        # else:
        #     if dest_lang == 'auto':
        #         if src_lang == lang_pair_prefer[0]:
        #             dest_lang = lang_pair_prefer[1]
        #         elif src_lang == lang_pair_prefer[1]:
        #             dest_lang = lang_pair_prefer[0]
        #         else:
        #             dest_lang = dest_lang_prefer

        self.outputText_.delete("1.0", tk.END)
        self.outputText_.insert(tk.END, "[Waiting for response...]")

        if engine == 'google':
            src_lang = 'auto' if src_lang_index == len(
                src_languages) - 1 else languages_for_google[src_lang_index]
            _, trans = GoogleTranslate(
                    content, src_language=src_lang, dest_language=languages_for_google[dest_lang_index])
        elif engine == 'baidu_api':
            src_lang = 'auto' if src_lang_index == len(
                src_languages) - 1 else languages_for_baidu_api[src_lang_index]
            trans = BaiduTranslate(
                content, src_language=src_lang, dest_language=languages_for_baidu_api[dest_lang_index])[1]
        else:
            trans = '[Please choose a translation engine]'

        self.outputText_.delete("1.0", tk.END)
        self.outputText_.insert(tk.END, trans)


if __name__ == '__main__':
    LoadSettings()
    gui = Gui()
