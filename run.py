if __name__ == "__main__":
    print("Initializing...", end="", flush=True)
    from selextrans.trans import Gui

    gui = Gui()
    print("Completed")
    gui.Loop()
