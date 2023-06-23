import os
import platform
import hashlib
import requests
import secrets
import pyperclip
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from tkinter import messagebox
# import asyncio
# import httpx
import time
import langid
import pynput.keyboard as keyboard
import re
from googletrans import Translator  # must be >=4.0.0rc1
from httpcore import SyncHTTPProxy
from urllib.parse import urlparse
import subprocess
import pytesseract
import concurrent.futures
import tiktoken
import openai

from selextrans.data_processing import DumpData, LoadData, configs, configs_file, settings, settings_file
from selextrans.paths import AbsolutePath
from selextrans.utils import KeyController, KeyListener, PrintScreen, PrintScreenBeautifully

# # const
# kText = 0
# kImage = 1

# golbal var
languages = []
src_languages = []
dest_languages = []
languages_for_tesseract = []

system_name = platform.system()

tessdata_dir_config = ''

copy_key = []


def LoadConfigs():
    global configs, languages, src_languages, dest_languages, languages_for_tesseract, tessdata_dir_config

    configs = LoadData(configs_file)
    languages = configs['languages']
    src_languages = languages + ['auto']
    dest_languages = languages
    languages_for_tesseract = configs['languages_for_tesseract']

    # customize language data loc
    tessdata_dir_config = '--tessdata-dir ' + \
        AbsolutePath(configs['tessdata_dir'])


def SaveConfigs():
    DumpData(configs_file, configs)


def LoadSettings():
    global settings, copy_key
    settings = LoadData(settings_file)
    copy_key = keyboard.HotKey.parse(settings['copy_key'])
    pytesseract.pytesseract.tesseract_cmd = settings['tesseract_cmd']


def SaveSettings():
    DumpData(settings_file, settings)


# directly load some data here
try:
    LoadConfigs()
    LoadSettings()
except Exception as e:
    messagebox.showerror(str(e))
    raise e


def PrintSceenToClipboard():
    '''
    Using tools for printscreen, not use now
    '''
    if system_name == 'Linux':  # linux
        try:
            subprocess.run(['gnome-screenshot', '-c', '-a'], check=True)
            return 1
        except subprocess.CalledProcessError:
            return 0
    elif system_name == 'Windows':  # Windows
        # KeyController().Type([keyboard.Key.shift, keyboard.Key.cmd, 's']) # bug here
        # return 1
        return 0
    elif system_name == 'Darwin':  # Macos
        try:
            subprocess.run(['screencapture', '-i', '-s', '-c'],
                           check=True)  # brew install pngpaste
            return 1
        except subprocess.CalledProcessError:
            return 0
    else:
        return 0


def ProcessText(text):
    '''
    Mostly for PDF; Process copied text and image ocr results
    '''
    def Replace(match):
        match_str = match.group(0)
        if match_str[0] == '—':
            return ''
        else:
            return ' '

    lang, _ = langid.classify(text)
    if lang in ['zh', 'ja']:  # Chinese, Japanese... do not need spaces to sep words
        # simply ignore '\r' '\n' '\f'
        return re.sub(r'[\r\n\f]+', '', text)
    else:
        # ignore em-dash '—' (\u1024) + new_line, for ocr results; a bunch of '/n' '\r' '\f' -> one space
        return re.sub(r'[\r\n\f]+|—\n', Replace, text)
        # return re.sub(r'[\r\n\f]+|—[\r\n]+', Replace, text)


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

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        src_lang = 'auto' if src_lang_index == len(
            src_languages) - 1 else BaiduAPITranslator.languages_for_baidu_api_[src_lang_index]
        _, trans = self.Translate(
            src_text, src_language=src_lang, dest_language=BaiduAPITranslator.languages_for_baidu_api_[dest_lang_index])
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, trans)


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
                    messagebox.showerror(
                        message='No http_proxy is set, but all_proxy is set')
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
        except IndexError: # this error always occurs when input is empty
            return 0, '[Error: ' + 'Empty input' + ']'
        except Exception as e:
            # raise e
            return 0, '[Error: ' + str(e) + ']'

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        src_lang = 'auto' if src_lang_index == len(
            src_languages) - 1 else GoogleTranslator.languages_for_google_[src_lang_index]
        _, trans = self.Translate(
            src_text, src_language=src_lang, dest_language=GoogleTranslator.languages_for_google_[dest_lang_index])
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, trans)


class OpenaiAPITranslator:

    def __init__(self, api_key, model='gpt-3.5-turbo', stream=True):
        openai.api_key = settings['openai_api_key']
        self.model_ = model
        self.stream_ = stream

    def NumTokensFromString(string, model_name='text-davinci-003'):
        '''Not use, just for future'''
        encoding = tiktoken.encoding_for_model(model_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def NumTokensFromMessages(messages, model="gpt-3.5-turbo"):
        '''Not use, just for future'''
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            print("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        if "gpt-3.5-turbo" in model:
            # every message follows <|start|>{role/name}\n{content}<|end|>\n
            tokens_per_message = 4
            tokens_per_name = -1  # if there's a name, the role is omitted
        elif "gpt-4-0314" in model:
            tokens_per_message = 3
            tokens_per_name = 1
        else:
            raise NotImplementedError(
                f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens.""")
        num_tokens = 0
        for message in messages:
            num_tokens += tokens_per_message
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
                if key == "name":
                    num_tokens += tokens_per_name
        num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
        return num_tokens

    def TranslateWithCompletion(self, src_text, src_language, dest_language):
        '''Not use, just for future'''
        try:
            prompt = f'Translate this into {dest_language}:\n\n{src_text}'
            response = openai.Completion.create(
                model=self.model_,
                prompt=prompt,
                temperature=0.3,
                max_tokens=4097 -
                OpenaiAPITranslator.NumTokensFromString(prompt, self.model_),
                top_p=1.0,

                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            return 1, response['choices'][0]['text'].strip()
        except Exception as e:
            return 0, '[Error: ' + str(e) + ']'

    def TranslateWithChatCompletion(self, src_text, src_language, dest_language):
        return openai.ChatCompletion.create(
            model=self.model_,
            messages=[
                {'role': 'user', 'content': f'Translate this into {dest_language}:\n\n{src_text}'}
            ],
            temperature=0,
            stream=self.stream_
        )

    def GetContentWithChatCompletionResponseChunk(chunk):
        content = chunk['choices'][0]['delta'].get('content')
        if content:
            return content.strip()
        else:
            return ''

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        try:
            response = self.TranslateWithChatCompletion(
                src_text, '', languages[dest_lang_index])
            tk_text.delete('1.0', tk.END)
            tk_text.insert(tk.END, '[Generating...]\n')
            for chunck in response:
                content = OpenaiAPITranslator.GetContentWithChatCompletionResponseChunk(
                    chunck)
                tk_text.insert(tk.END, content)
            tk_text.delete('1.0', '2.0')
        except Exception as e:
            tk_text.delete("1.0", tk.END)
            tk_text.insert(tk.END, '[Error: ' + str(e) + ']')


class Gui:
    def __init__(self):

        # init translator
        engine = settings['engine']
        if engine == 'google':
            self.translator_ = GoogleTranslator()
        elif engine == 'baidu_api':
            self.translator_ = BaiduAPITranslator(
                settings['appid_for_baidu_api'], settings['private_key_for_baidu_api'])
        elif engine == 'openai_api':
            self.translator_ = OpenaiAPITranslator(settings['openai_api_key'])
        else:
            messagebox.showerror(message='Please choose a translation engine')
            print('Please choose a translation engine')
            exit(0)

        # init gui
        self.root_ = tk.Tk()
        self.root_.title('Selextrans')
        self.root_.attributes("-topmost", True)
        self.root_.iconphoto(True, tk.PhotoImage(
            file=AbsolutePath(configs['icon'])))

        global_font = tkfont.Font(size=15)
        self.root_.option_add('*Font', global_font)

        self.src_lang_combox_ = ttk.Combobox(
            self.root_, values=src_languages)
        self.inputText_ = tk.Text(self.root_, height=18, width=30)
        self.row_frame_ = tk.Frame(
            self.root_, highlightthickness=0, borderwidth=0)
        self.dest_lang_combox_ = ttk.Combobox(
            self.row_frame_, values=dest_languages)
        # self.record_btn_ = tk.Button(self.row_frame_, text='Record', command=lambda event: 1)
        self.outputText_ = tk.Text(
            self.root_, height=18, width=30)

        if settings['mode'] == 'dark':
            self.inputText_.configure(
                background='#292421', foreground='white', insertbackground='white')
            self.outputText_.configure(
                background='#292421', foreground='white', insertbackground='white')
            # self.record_btn_.configure(
            #     background='#292421', foreground='white', activebackground='white', activeforeground='black')

            # foreground: text, fieldbackground: background area, background: drop-down box, arrowcolor: arrow color
            # ttk.Style().configure('TCombobox', foreground='white', fieldbackground='#292421', background='#292421', arrowcolor='white') # can work on Linux but not on Windows
            style = ttk.Style()
            style.theme_create('combobox_style', settings={
                'TCombobox': {'configure': {
                    'foreground': 'white',
                    'fieldbackground': '#292421',
                    'background': '#464547',
                    'arrowcolor': 'white'
                }
                }
            })
            style.theme_use('combobox_style')

            # for drop-down list
            self.root_.option_add('*TCombobox*Listbox*Foreground', 'white')
            self.root_.option_add('*TCombobox*Listbox*Background', '#292421')

        self.src_lang_combox_.grid(row=0, column=0, sticky=tk.EW)
        self.inputText_.grid(row=1, column=0, sticky=tk.NSEW)
        self.row_frame_.grid(row=2, column=0, sticky=tk.EW)
        self.dest_lang_combox_.grid(row=0, column=0, sticky=tk.NSEW)
        # self.record_btn_.grid(row=0, column=1, sticky=tk.NSEW)
        self.outputText_.grid(row=3, column=0, sticky=tk.NSEW)

        # set weight
        self.root_.columnconfigure(0, weight=1)
        self.root_.rowconfigure(1, weight=1)
        self.root_.rowconfigure(3, weight=1)
        self.row_frame_.rowconfigure(0, weight=1)
        self.row_frame_.columnconfigure(0, weight=1)

        self.src_lang_combox_.current(len(src_languages) - 1)
        self.dest_lang_combox_.current(0)

        self.kbController_ = KeyController()

        try:
            self.listener_ = KeyListener({settings['text_translate_shortcut_key']: self.TextTranslate,
                                          settings['screenshot_translate_shortcut_key']: self.ReigisterSrceenshotTranslateToMainLoop})
            # self.listener_ = KeyListener({settings['text_translate_shortcut_key']: self.TextTranslate,
            #                               settings['screenshot_translate_shortcut_key']: self.SrceenshotTranslate})
        except Exception as e:
            messagebox.showerror(str(e))
            raise e

        self.listener_.start()
        # self.listener_.join()

        # self.src_lang_combox_.bind(
        #     '<<ComboboxSelected>>', self.HandleSrcLanguageSelect)
        # self.dest_lang_combox_.bind(
        #     '<<ComboboxSelected>>', self.HandleDestLanguageSelect)

        # backend thread for time consuming tasks
        self.thread_pool_ = concurrent.futures.ThreadPoolExecutor(
            max_workers=1)

        self.root_.mainloop()

    def TextTranslate(self):

        pre_content = pyperclip.paste()

        # with self.kbController_.pressed(kb.Key.ctrl):
        #   self.kbController_.press('c')

        # copy the selected text to clipboard
        self.kbController_.Type(copy_key)
        # sleep here to wait content copied to the clipboard
        time.sleep(0.1)
        content = pyperclip.paste()
        pyperclip.copy(pre_content)  # recover
        self.inputText_.delete("1.0", tk.END)
        self.inputText_.insert(tk.END, content)

        self.RegisterDoTrans()

    def SrceenshotTranslate(self):
        '''
        print sreen then ocr then translate
        '''
        src_lang_index = self.src_lang_combox_.current()
        if src_lang_index == len(src_languages) - 1:
            self.inputText_.delete("1.0", tk.END)
            self.outputText_.delete("1.0", tk.END)
            self.outputText_.insert(
                tk.END, "[Please choose a specific language for ocr]")
            return
        img = PrintScreenBeautifully()
        if not img:
            return
        content = pytesseract.image_to_string(
            image=img, lang=languages_for_tesseract[src_lang_index], config=tessdata_dir_config)
        self.inputText_.delete("1.0", tk.END)
        self.inputText_.insert(tk.END, content)

        self.RegisterDoTrans()

    def ReigisterSrceenshotTranslateToMainLoop(self):
        '''
        PrintScreenBeautifully() use pyqt5, pyqt5 requires QApplication to be created  at main thread
        '''
        self.root_.after(0, self.SrceenshotTranslate)

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

        self.translator_.TranslateWrapper(self.outputText_,
                                          content, src_lang_index, dest_lang_index)

    # def RegisterTextTranslate(self):
    #     self.thread_pool_.submit(self.TextTranslate)

    # def RegisterScreenshotTranslate(self):
    #     self.thread_pool_.submit(self.SrceenshotTranslate)

    def RegisterDoTrans(self):
        self.thread_pool_.submit(self.DoTrans)


def Start():
    Gui()
