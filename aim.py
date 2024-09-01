from subprocess import getoutput as out, Popen as run, DEVNULL

import tkinter as tk
from PIL.ImageTk import PhotoImage
from PIL import Image
import numpy as num
from time import sleep
from threading import Thread
import cv2 as cv

COLOR = num.array([217, 37, 217])  # magenta
TOLERANCE, BOX = 50, 400

def getRes():
    for line in out("wlr-randr").split('\n'):
        if "current" in line: return map(int, line.split()[0].split('x'))

DEV = "/dev/video0"
W, H = getRes()

geom = f"{(W-BOX)//2},{(H-BOX)//2} {BOX}x{BOX}"
exe = out("which wl-screenrec")

rec = run(["sudo", "-E", exe, "-g", geom, "--ffmpeg-muxer", "v4l2", "-f", DEV], stdout=DEVNULL)

target, mask = None, None
def process(frame):
    diff = num.abs(frame[:,:,:3] - COLOR)
    mask = num.all(diff <= TOLERANCE, axis=2)

    found = num.argwhere(mask)
    if found.size > 0:
        center = num.mean(found, axis=0).astype(int)  # "CoM"
        return tuple(center), mask
    return None, mask

class Debug:
    def __init__(self):
        self.window = tk.Tk()
        self.window.attributes("-type", "dialog")
        self.canvas = tk.Canvas(self.window, width=400, height=400, bg="black")
        self.canvas.pack()

    def update(self, target, mask):
        heatmap = ?
        photo = PhotoImage(image=Image.fromarray(heatmap))
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo

        self.canvas.create_line(200, 0, 200, 400, fill="green")
        self.canvas.create_line(0, 200, 400, 200, fill="green")

        if target:
            x, y = 399 - target[1], target[0]
            self.canvas.create_oval(x-5, y-5, x+5, y+5, outline="white")
            self.canvas.create_line(x, 0, x, 400, fill="yellow")
            self.canvas.create_line(0, y, 400, y, fill="yellow")
            self.canvas.create_text(10, 10, anchor=tk.NW, text=f"({target[0]}, {target[1]})", fill="yellow")

        self.window.update()

def capture():
    global target, mask
    cap = cv.VideoCapture(DEV)
    if not cap.isOpened():
        raise IOError("ERROR: could not open video device.")
    while True:
        ret, frame = cap.read()
        if ret:
            target, mask = process(frame)
            if target: print(f"Found at {target}")
        sleep(0.01)

Thread(target=capture, daemon=True).start()
debug = Debug()

try:
    while True:
        if mask is not None: debug.update(target, mask)
except Exception as e: pass
finally:
    debug.window.destroy()
    rec.terminate()
