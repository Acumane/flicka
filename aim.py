from subprocess import getoutput as out, Popen as run, DEVNULL
from tkinter import Tk as Window, Label
from PIL.ImageTk import PhotoImage
from PIL import Image
import cv2 as CV

def display(capture):
    window = Window()
    window.attributes("-type", "dialog")
    window.title("Capture")
    label = Label(window)
    label.pack()

    def updateFrame():
        ret, frame = capture.read()
        if ret:
            img = PhotoImage(image=Image.fromarray(frame))
            label.config(image=img)
            label.image = img

        window.after(10, updateFrame) # ~100 FPS

    updateFrame()
    window.mainloop()
    capture.release() # cleanup on close

def getRes():
    for line in out("wlr-randr").split('\n'):
        if "current" in line: return map(int, line.split()[0].split('x'))

DEV = "/dev/video0"
W, H = getRes()
BOX = 400

geom = f"{(W-BOX)//2},{(H-BOX)//2} {BOX}x{BOX}"
exe = out("which wl-screenrec")

rec = run(["sudo", "-E", exe, "-g", geom, "--ffmpeg-muxer", "v4l2", "-f", DEV], stdout=DEVNULL)

try:
    capture = CV.VideoCapture("/dev/video0")

    if not capture.isOpened():
        raise IOError("ERROR: could not open video device.")
    display(capture)

finally:
    rec.terminate()
