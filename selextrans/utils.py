from pynput import keyboard
import tkinter as tk

import sys
from PyQt5.QtCore import Qt, QRect, QPoint
from PyQt5.QtWidgets import QWidget, QApplication, QDesktopWidget
from PyQt5.QtGui import QPainter, QBitmap, QCursor, QPen, QBrush

import pyautogui


class KeyController(keyboard.Controller):
    def __init__(self):
        super().__init__()

    def Type(self, keys):
        for key in keys:
            self.press(key)
        for key in keys:
            self.release(key)


class KeyListener(keyboard.Listener):
    '''
    Customized key listener for key combinations
    '''

    def __init__(self, keys_to_callback):

        self.pressed_ = set()
        self.keys_to_callback_ = {frozenset([self.canonical(
            key) for key in keyboard.HotKey.parse(k)]): v for k, v in keys_to_callback.items()}
        # print(self.keys_to_callback_)

        super().__init__(on_press=self.OnPress, on_release=self.OnRelease)

    def OnPress(self, key):
        # print(f'Press {self.canonical(key)}')
        # handle the problem that any key controller tries to press the pressed key
        if self.canonical(key) in self.pressed_:
            return
        self.pressed_.add(self.canonical(key))

        callback = self.keys_to_callback_.get(frozenset(self.pressed_))
        if callback:
            callback()

    def OnRelease(self, key):
        # print(f'Release {self.canonical(key)}')
        try:
            self.pressed_.remove(self.canonical(key))
        except KeyError as e:
            pass


def PrintScreen(area=True):
    '''
    use tkinter, return PIL.Image.Image
    '''
    if not area:
        return pyautogui.screenshot()

    def OnMouseLeftDown(event):
        nonlocal start_x, start_y, rectangle_area
        # print("Start selecting")
        start_x, start_y = event.x, event.y
        rectangle_area = canvas.create_rectangle(
            start_x, start_y, start_x+1, start_y+1, outline='#ea66a6',  width=3)

    def OnMouseRightClick(event):
        # print("Selecting canceled")
        root.destroy()

    def OnMouseLeftUp(event):
        # print("Stop selecting")
        nonlocal img
        root.destroy()
        # calc top-left , width & height
        top_left = [0, 0]
        width = start_x - event.x()
        height = start_y - event.y()
        if width < 0:
            top_left[0] = start_x
            width = -width
        else:
            top_left[0] = event.x()
        if height < 0:
            top_left[1] = start_y
            height = -height
        else:
            top_left[1] = event.y()
        if width == 0 or height == 0:
            return
        # print screen
        # faster than ImageGrab.grab()
        img = pyautogui.screenshot(
            region=(top_left[0], top_left[1], width, height))

    def OnMouseMove(event):
        nonlocal rectangle_area
        if rectangle_area:
            canvas.coords(rectangle_area, start_x, start_y, event.x, event.y)

    # area
    root = tk.Tk()

    root.overrideredirect(True)

    root.attributes("-topmost", True)

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    # root.geometry("%dx%d+0+0" % (screen_width, screen_height))

    root.wait_visibility(root)
    root.attributes("-alpha", 0.2)  # not to 0.0, or lines can not be seen

    canvas = tk.Canvas(root, height=screen_height, width=screen_width)
    canvas.pack()
    root.configure(cursor='crosshair')

    rectangle_area = None
    start_x, start_y = 0, 0

    img = None

    root.bind("<Button-1>", OnMouseLeftDown)
    root.bind("<ButtonRelease-1>", OnMouseLeftUp)
    root.bind("<Motion>", OnMouseMove)
    root.bind("<Button-3>", OnMouseRightClick)
    root.mainloop()
    return img


def PrintScreenBeautifully(area=True):
    '''
    use pyqt5, return PIL.Image.Image
    '''
    class ScreenPrinter(QWidget):

        def __init__(self):
            self.app_ = QApplication(sys.argv)

            super().__init__()
            self.setWindowFlags(Qt.FramelessWindowHint |
                                Qt.WindowStaysOnTopHint)
            self.setStyleSheet('''background-color:black; ''')
            self.setWindowOpacity(0.5)  # alpha
            dw = QDesktopWidget()
            screen_width = dw.screenGeometry().width()
            screen_height = dw.screenGeometry().height()
            self.setGeometry(0, 0, screen_width, screen_width)

            self.mask_ = QBitmap(screen_width, screen_height)

            self.start_point_ = QPoint(0, 0)
            self.end_point_ = QPoint(0, 0)
            self.img_ = None
            self.is_pressing_left_button_ = False

            self.showFullScreen() # fullscreen, or the mask may not be cover fullscreen (esp. tkinter windows) (don't know reason)
            self.setWindowState(self.windowState() & ~Qt.WindowFullScreen) # show the taskbar
            self.app_.exec_()

        def paintEvent(self, event):
            # mask all black
            self.mask_.fill(Qt.black)
            # draw a rect on mask
            mask_painter = QPainter(self.mask_)
            mask_painter.setBrush(QBrush(Qt.white))
            rect = QRect(self.start_point_, self.end_point_)
            mask_painter.drawRect(rect)
            self.setMask(self.mask_)

            # draw border
            painter = QPainter(self)
            painter.setPen(QPen(Qt.red, 3))
            painter.drawRect(rect)

        def mousePressEvent(self, event):
            if event.button() == Qt.LeftButton:
                self.start_point_ = event.pos()
                self.is_pressing_left_button_ = True
            elif event.button() == Qt.RightButton:
                self.close()

        def mouseMoveEvent(self, event):
            if self.is_pressing_left_button_:
                self.end_point_ = event.pos()
                self.update()

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.LeftButton:
                # calc top-left , width & height
                top_left = [0, 0]
                width = self.start_point_.x() - event.x()
                height = self.start_point_.y() - event.y()
                if width < 0:
                    top_left[0] = self.start_point_.x()
                    width = -width
                else:
                    top_left[0] = event.x()
                if height < 0:
                    top_left[1] = self.start_point_.y()
                    height = -height
                else:
                    top_left[1] = event.y()
                if width == 0 or height == 0:
                    self.close()
                    return
                # print screen
                self.img_ = pyautogui.screenshot(region=(
                    top_left[0], top_left[1], width, height))  # faster than ImageGrab.grab()
                # self.is_pressing_left_button_ = False
                self.close()

        def keyPressEvent(self, event):
            if event.key() == Qt.Key_Escape:
                self.close()

        def enterEvent(self, event):
            QApplication.setOverrideCursor(QCursor(Qt.CrossCursor))

        def leaveEvent(self, event):
            QApplication.restoreOverrideCursor()

    if not area:
        return pyautogui.screenshot()

    sp = ScreenPrinter()
    return sp.img_
