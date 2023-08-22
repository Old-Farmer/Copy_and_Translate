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
import gc

from selextrans.data_processing import (
    DumpData,
    LoadData,
    configs,
    configs_file,
    settings,
    settings_file,
)
from selextrans.paths import AbsolutePath
from selextrans.utils import KeyController, KeyListener, PrintScreenBeautifully

# The first call is always slow Because langid should do some init, So we call it here
langid.classify("")

# # const
# kText = 0
# kImage = 1

# global var
languages = []
src_languages = []
dest_languages = []
languages_for_tesseract = []

system_name = platform.system()

tessdata_dir_config = ""

copy_key = []


def LoadConfigs():
    global configs, languages, src_languages, dest_languages, languages_for_tesseract, tessdata_dir_config

    configs = LoadData(configs_file)
    languages = configs["languages"]
    src_languages = languages + ["auto"]
    dest_languages = languages
    languages_for_tesseract = configs["languages_for_tesseract"]

    # customize language data loc
    tessdata_dir_config = "--tessdata-dir " + AbsolutePath(configs["tessdata_dir"])


def SaveConfigs():
    DumpData(configs_file, configs)


def LoadSettings():
    global settings, copy_key
    settings = LoadData(settings_file)
    copy_key = keyboard.HotKey.parse(settings["copy_key"])
    pytesseract.pytesseract.tesseract_cmd = settings["tesseract_cmd"]


def SaveSettings():
    DumpData(settings_file, settings)


def PrintScreenToClipboard():
    """
    Use other tools for printing screen, not use now
    """
    if system_name == "Linux":  # linux
        try:
            subprocess.run(["gnome-screenshot", "-c", "-a"], check=True)
            return 1
        except subprocess.CalledProcessError:
            return 0
    elif system_name == "Windows":  # Windows
        # KeyController().Type([keyboard.Key.shift, keyboard.Key.cmd, 's']) # bug here
        # return 1
        return 0
    elif system_name == "Darwin":  # Macos
        try:
            subprocess.run(
                ["screencapture", "-i", "-s", "-c"], check=True
            )  # brew install pngpaste
            return 1
        except subprocess.CalledProcessError:
            return 0
    else:
        return 0


def ProcessText(text):
    """
    Mostly for PDF; Process copied text and image ocr results
    """

    def Replace(match):
        match_str = match.group()
        if match_str[0] == "—":
            return ""
        else:
            return " "

    text = text.strip()
    lang, _ = langid.classify(text)
    if lang in ["zh", "ja"]:  # Chinese, Japanese... do not need spaces to sep words
        # simply ignore blank characters
        return re.sub(r"\s+", "", text)
    else:
        # ignore em-dash '—' (\u1024) + new_line (\r\n on Windows & \n on Unix-like), for ocr results; a bunch of blank characters -> one space
        return re.sub(r"\s+|—\r?\n", Replace, text)


class BaiduAPITranslator:
    def __init__(self):
        self.appid_ = settings["appid_for_baidu_api"]
        self.private_key_ = settings["private_key_for_baidu_api"]
        self.request_url_ = settings["request_url_for_baidu_api"]
        self.languages_for_baidu_api_ = configs["languages_for_baidu_api"]

    def Translate(self, src_text, src_language="auto", dest_language="en"):
        def Md5Encrypt(input_string):
            md5_hash = hashlib.md5()
            md5_hash.update(input_string.encode("utf-8"))
            encrypted_string = md5_hash.hexdigest()
            return encrypted_string

        def GenerateSalt(length=16):
            salt = secrets.token_hex(length // 2)
            return salt

        if self.appid_ == "":
            return "[Please offer appid and private key]"

        params = {
            "q": src_text,
            "from": src_language,
            "to": dest_language,
            "appid": self.appid_,
            "salt": GenerateSalt(),
            "sign": "",
        }

        params["sign"] = Md5Encrypt(
            params["appid"] + params["q"] + params["salt"] + self.private_key_
        )

        # async with httpx.AsyncClient() as client:
        #   r = await client.get(request_url_, params=params)

        r = requests.get(self.request_url_, params=params)

        if r.status_code != 200:
            return 0, "Error happened, try again!"
        else:
            response = r.json()
            if response.get("trans_result") is not None:
                result = response["trans_result"]
                # return 1, 'src: ' + result[0]['src'] + '\n' + 'translation: '+ result[0]['dst']
                return 1, result[0]["dst"]
            else:
                return response["error_code"], f"[Error: {response['error_msg']}]"

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        src_lang = (
            "auto"
            if src_lang_index == len(src_languages) - 1
            else self.languages_for_baidu_api_[src_lang_index]
        )
        _, trans = self.Translate(
            src_text,
            src_language=src_lang,
            dest_language=self.languages_for_baidu_api_[dest_lang_index],
        )
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, trans)


class GoogleTranslator:
    """ """

    def __init__(self):
        self.languages_for_google_ = configs["languages_for_google"]

        # check if proxy has been set manually
        if settings["https_proxy"]:
            if system_name == "Linux":
                os.environ["all_proxy"] = ""
            try:
                url = urlparse(settings["https_proxy"])

                self.google_translator = Translator(
                    proxies={
                        "https": SyncHTTPProxy(
                            (
                                bytes(url.scheme, encoding="utf-8"),
                                bytes(url.hostname, encoding="utf-8"),
                                int(url.port),
                                b"",
                            )
                        )
                    },
                )
            except:
                messagebox.showerror(
                    message="Please set correct https proxy, or just leave it empty",
                )
                print("Please set correct https proxy, or just leave it empty")
                exit(0)
            return

        if system_name == "Linux" or system_name == "Darwin":  # linux or mac
            all_proxy = os.environ.get("all_proxy")
            if all_proxy and urlparse(all_proxy).scheme == "socks":
                if os.environ.get("https_proxy"):
                    # socks scheme is not supported by httpx library, so we just use https_proxy
                    os.environ["all_proxy"] = os.environ["https_proxy"]
                else:
                    messagebox.showerror(
                        message="No https_proxy is set, but all_proxy is set"
                    )
                    print("No https_proxy is set, but all_proxy is set")
                    exit(0)
            self.google_translator = Translator()
        elif system_name == "Windows":  # windows
            import winreg

            INTERNET_SETTINGS = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )

            def GetProxySettings():
                try:
                    proxy_enabled = winreg.QueryValueEx(
                        INTERNET_SETTINGS, "ProxyEnable"
                    )[0]
                    if proxy_enabled == 1:
                        proxy_server = winreg.QueryValueEx(
                            INTERNET_SETTINGS, "ProxyServer"
                        )[0]
                        return proxy_server
                    else:
                        return None
                except FileNotFoundError:
                    return None

            proxy = GetProxySettings()
            if proxy:
                ip, port = proxy.split(":")
                self.google_translator = Translator(
                    proxies={
                        "https": SyncHTTPProxy((b"http", ip.encode(), int(port), b""))
                    }
                )  # if can not get proxy from env var, set the proxy manually
            else:
                self.google_translator = Translator()

    def Translate(self, src_text, src_language="auto", dest_language="en"):
        try:
            r = self.google_translator.translate(
                src_text, src=src_language, dest=dest_language
            )
            return 1, r.text
        except IndexError:  # this error always occurs when input is empty
            return 0, "[Error: Empty input]"
        except Exception as e:
            # raise e
            return 0, f"[Error: {e}]"

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        src_lang = (
            "auto"
            if src_lang_index == len(src_languages) - 1
            else self.languages_for_google_[src_lang_index]
        )
        _, trans = self.Translate(
            src_text,
            src_language=src_lang,
            dest_language=self.languages_for_google_[dest_lang_index],
        )
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, trans)


class OpenaiAPITranslator:
    def __init__(self, model="gpt-3.5-turbo", stream=True):
        openai.api_key = settings["openai_api_key"]
        self.model_ = model
        self.stream_ = stream

    def NumTokensFromString(string, model_name="text-davinci-003"):
        """Not use, just for future"""
        encoding = tiktoken.encoding_for_model(model_name)
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def NumTokensFromMessages(messages, model="gpt-3.5-turbo"):
        """Not use, just for future"""
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
                f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
            )
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
        """Not use, just for future"""
        try:
            prompt = f"Translate this into {dest_language}:\n\n{src_text}"
            response = openai.Completion.create(
                model=self.model_,
                prompt=prompt,
                temperature=0.3,
                max_tokens=4097
                - OpenaiAPITranslator.NumTokensFromString(prompt, self.model_),
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
            )
            return 1, response["choices"][0]["text"].strip()
        except Exception as e:
            return 0, f"[Error: {e}]"

    def TranslateWithChatCompletion(self, src_text, src_language, dest_language):
        return openai.ChatCompletion.create(
            model=self.model_,
            messages=[
                {
                    "role": "user",
                    "content": f"Translate this into {dest_language}:\n\n{src_text}",
                }
            ],
            temperature=0,
            stream=self.stream_,
        )

    def GetContentWithChatCompletionResponseChunk(chunk):
        content = chunk["choices"][0]["delta"].get("content")
        if content:
            return content.strip()
        else:
            return ""

    def TranslateWrapper(self, tk_text, src_text, src_lang_index, dest_lang_index):
        try:
            response = self.TranslateWithChatCompletion(
                src_text, "", languages[dest_lang_index]
            )
            if self.stream_:
                tk_text.delete("1.0", tk.END)
                tk_text.insert(tk.END, "[Generating...]\n")
                for chunk in response:
                    content = (
                        OpenaiAPITranslator.GetContentWithChatCompletionResponseChunk(
                            chunk
                        )
                    )
                    tk_text.insert(tk.END, content)
                tk_text.delete("1.0", "2.0")
            else:
                tk_text.delete("1.0", tk.END)
                tk_text.insert(tk.END, response["choices"][0]["message"]["content"])
        except Exception as e:
            tk_text.delete("1.0", tk.END)
            tk_text.insert(tk.END, f"[Error: {e}]")


class Gui:
    def __init__(self):
        # init
        self.root_ = tk.Tk()
        # create themes
        style = ttk.Style()
        style.theme_create(
            "dark",
            settings={
                "TCombobox": {
                    "configure": {
                        "foreground": "white",
                        "fieldbackground": "#292421",
                        "background": "#464547",
                        "arrowcolor": "white",
                    }
                }
            },
        )
        self.Init()

    def Init(self):
        # data init
        try:
            LoadConfigs()
            LoadSettings()
        except Exception as e:
            messagebox.showerror(message=str(e))
            raise e
        self.SetTranslator()

        # init gui
        self.root_.title("Selextrans")
        self.root_.attributes("-topmost", True)
        self.root_.iconphoto(True, tk.PhotoImage(file=AbsolutePath(configs["icon"])))

        global_font = tkfont.Font(size=15)
        self.root_.option_add("*Font", global_font)

        self.command_entry_ = tk.Entry(self.root_)
        self.src_lang_combobox_ = ttk.Combobox(self.root_, values=src_languages)
        self.input_text_ = tk.Text(self.root_, height=18, width=30)
        self.row_frame_ = tk.Frame(self.root_, highlightthickness=0, borderwidth=0)
        self.dest_lang_combobox_ = ttk.Combobox(self.row_frame_, values=dest_languages)
        # self.record_btn_ = tk.Button(self.row_frame_, text='Record', command=lambda event: 1)
        self.output_text_ = tk.Text(self.root_, height=18, width=30)

        # theme set
        if settings["mode"] == "dark":
            self.command_entry_.configure(
                background="#292421", foreground="white", insertbackground="white"
            )
            self.input_text_.configure(
                background="#292421", foreground="white", insertbackground="white"
            )
            self.output_text_.configure(
                background="#292421", foreground="white", insertbackground="white"
            )
            # self.record_btn_.configure(
            #     background='#292421', foreground='white', activebackground='white', activeforeground='black')

            # foreground: text, fieldbackground: background area, background: drop-down box, arrowcolor: arrow color
            # ttk.Style().configure('TCombobox', foreground='white', fieldbackground='#292421', background='#292421', arrowcolor='white') # can work on Linux but not on Windows
            style = ttk.Style()
            style.theme_use("dark")

            # for drop-down list
            self.root_.option_add("*TCombobox*Listbox*Foreground", "white")
            self.root_.option_add("*TCombobox*Listbox*Background", "#292421")

        # self.command_entry_.grid(row=0, column=0, sticky=tk.EW)
        self.src_lang_combobox_.grid(row=1, column=0, sticky=tk.EW)
        self.input_text_.grid(row=2, column=0, sticky=tk.NSEW)
        self.row_frame_.grid(row=3, column=0, sticky=tk.EW)
        self.dest_lang_combobox_.grid(row=0, column=0, sticky=tk.NSEW)
        # self.record_btn_.grid(row=0, column=1, sticky=tk.NSEW)
        self.output_text_.grid(row=4, column=0, sticky=tk.NSEW)

        # set weight
        self.root_.columnconfigure(0, weight=1)
        self.root_.rowconfigure(2, weight=1)
        self.root_.rowconfigure(4, weight=1)
        self.row_frame_.rowconfigure(0, weight=1)
        self.row_frame_.columnconfigure(0, weight=1)

        self.src_lang_combobox_.current(len(src_languages) - 1)
        self.dest_lang_combobox_.current(0)

        self.kbController_ = KeyController()

        # listen when the window isn't focused
        try:
            self.listener_ = KeyListener(
                {
                    settings["text_translate_shortcut_key"]: self.TextTranslate,
                    settings[
                        "screenshot_translate_shortcut_key"
                    ]: self.RegisterScreenshotTranslateToMainLoop,
                }
            )
            # self.listener_ = KeyListener({settings['text_translate_shortcut_key']: self.TextTranslate,
            #                               settings['screenshot_translate_shortcut_key']: self.ScreenshotTranslate})
        except Exception as e:
            messagebox.showerror(message=str(e))
            raise e
        self.listener_.start()
        # self.listener_.join()

        # backend threads for time consuming tasks and some ui updates
        # as tkinter is thread safe, we simply do some ui updates in the backend threads for convenience
        self.thread_pool_ = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        # listen when the window is focused
        def TextSelectAll(event):
            """ctrl + a to select all"""
            event.widget.tag_add("sel", "1.0", "end")
            return "break"

        self.input_text_.bind("<Control-a>", TextSelectAll)
        self.input_text_.bind("<Control-A>", TextSelectAll)
        self.input_text_.bind(
            "<Return>", lambda event: self.thread_pool_.submit(self.DoTrans, True)
        )
        self.root_.bind("<F5>", self.Refresh)

        def ToggleCommandEntry(event):
            if not self.command_entry_.winfo_viewable():
                self.command_entry_.grid(row=0, column=0, sticky=tk.EW)
                self.command_entry_.focus()
            else:
                self.command_entry_.grid_forget()

        self.root_.bind(
            "<F1>",
            ToggleCommandEntry,
        )

        def EntrySelectAll(event):
            """ctrl + a to select all"""
            event.widget.select_range(0, tk.END)
            return "break"

        self.command_entry_.bind("<Control-a>", EntrySelectAll)
        self.command_entry_.bind("<Control-A>", EntrySelectAll)
        self.command_entry_.bind("<Return>", self.HandleCommand)

    def Loop(self):
        self.root_.mainloop()

    def Refresh(self, event):
        self.command_entry_.grid_forget()  # hide it, or the ui will not be normal
        geometry_info = self.root_.geometry()
        self.root_.withdraw()
        ttk.Style().theme_use("default")
        self.root_.option_clear()
        self.listener_.stop()
        self.Init()
        self.root_.geometry(geometry_info)
        self.root_.deiconify()
        gc.collect()

    def SetTranslator(self):
        engine = settings["engine"]
        if engine == "google":
            self.translator_ = GoogleTranslator()
        elif engine == "baidu_api":
            self.translator_ = BaiduAPITranslator()
        elif engine == "openai_api":
            self.translator_ = OpenaiAPITranslator(settings["openai_api_key"])
            # self.translator_ = OpenaiAPITranslator(settings['openai_api_key'], stream=False)
        else:
            messagebox.showerror(message="Please choose a translation engine")
            print("Please choose a translation engine")
            exit(0)

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

        self.RegisterDoTrans(content=content)

    def ScreenshotTranslate(self):
        """
        print screen then ocr then translate
        """
        src_lang_index = self.src_lang_combobox_.current()
        if src_lang_index == len(src_languages) - 1:
            self.input_text_.delete("1.0", tk.END)
            self.output_text_.delete("1.0", tk.END)
            self.output_text_.insert(
                tk.END, "[Please choose a specific language for ocr]"
            )
            return
        img = PrintScreenBeautifully()
        if not img:
            return
        try:
            content = pytesseract.image_to_string(
                image=img,
                lang=languages_for_tesseract[src_lang_index],
                config=tessdata_dir_config,
            )
        except Exception as e:
            self.input_text_.delete("1.0", tk.END)
            self.output_text_.delete("1.0", tk.END)
            self.output_text_.insert(tk.END, f"[Error: {e}]")
            print(e)
            return

        self.RegisterDoTrans(content=content)

    def RegisterScreenshotTranslateToMainLoop(self):
        """
        PrintScreenBeautifully() use pyqt5, pyqt5 requires QApplication to be created at main thread
        """
        self.root_.after(0, self.ScreenshotTranslate)

    def DoTrans(self, content_from_input_text=False, content=""):
        if content_from_input_text:
            content = self.input_text_.get("1.0", tk.END)
            # print(content)

        # trans = BaiduTranslate(content.replace('\n', '\\n'), 'en')[1].replace('\\', '\n') # baidu api has some problems with '\n'

        content = ProcessText(content)
        # print(content)
        self.input_text_.delete("1.0", tk.END)
        self.input_text_.insert(tk.END, content)

        self.output_text_.delete("1.0", tk.END)
        self.output_text_.insert(tk.END, "[Waiting for response...]")

        src_lang_index = self.src_lang_combobox_.current()
        dest_lang_index = self.dest_lang_combobox_.current()

        self.translator_.TranslateWrapper(
            self.output_text_, content, src_lang_index, dest_lang_index
        )

    # def RegisterTextTranslate(self):
    #     self.thread_pool_.submit(self.TextTranslate)

    # def RegisterScreenshotTranslate(self):
    #     self.thread_pool_.submit(self.ScreenshotTranslate)

    def RegisterDoTrans(self, content_from_input_text=False, content=""):
        self.thread_pool_.submit(self.DoTrans, content_from_input_text, content)

    def HandleCommand(self, event):
        command = self.command_entry_.get()
        command_args = command.split(" ")
        result = True
        try:
            # args: set key string_value
            if (
                len(command_args) == 3
                and command_args[0] == "set"
                and settings.get(command_args[1])
            ):
                settings[command_args[1]] = command_args[2]
                SaveSettings()
            elif len(command_args) == 1 and command_args[0] in ("help", "h"):
                self.output_text_.delete("1.0", tk.END)
                self.output_text_.insert(
                    tk.END,
                    "Help of all commands\n\
Usage:\n\
1. set <key> <string_value>        Set a known key value(string type) to settings.json",
                )
            else:
                result = False
        except IndexError:
            result = False
        self.command_entry_.delete(0, tk.END)
        if not result:
            self.output_text_.delete("1.0", tk.END)
            self.output_text_.insert(tk.END, "[Please input a correct command]")
        else:
            # self.command_entry_.grid_forget()  # successful, hide the command entry
            pass
