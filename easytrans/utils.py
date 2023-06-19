from pynput import keyboard


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
        if self.canonical(key) in self.pressed_: # handle the problem that any key controller tries to press the pressed key
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
