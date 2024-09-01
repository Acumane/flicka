from subprocess import getoutput as out, Popen as run, DEVNULL

import tkinter as tk
from PIL.ImageTk import PhotoImage
from PIL import Image
import numpy as num
from time import sleep
from threading import Thread
import cv2 as cv
from math import sqrt

TOL, BOX = ?, 400
HSV = (?, ?, ?)  # ~magenta

def getRes():
    for line in out("wlr-randr").split('\n'):
        if "current" in line: return map(int, line.split()[0].split('x'))

DEV = "/dev/video0"
W, H = getRes()

geom = f"{(W-BOX)//2},{(H-BOX)//2} {BOX}x{BOX}"
exe = out("which wl-screenrec")

rec = run(["sudo", "-E", exe, "-g", geom, "--ffmpeg-muxer", "v4l2", "-f", DEV], stdout=DEVNULL)

target, mask, bBoxes = None, None, []
def process(frame):
    global bBoxes
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)
    lower = num.array([HSV[0] - TOL, HSV[1], HSV[2]])
    upper = num.array([HSV[0] + TOL, 255, 255])
    outline = cv.inRange(hsv, lower, upper)

    # Detect names, healthbars:
    contours, _ = cv.findContours(outline, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    bBoxes = []
    for contour in contours:
        x, y, w, h = cv.boundingRect(contour)
        if (w / h) > 2 and cv.contourArea(contour) > 100:  # WIP
            bBoxes.append((x, y, w, h))

    found = num.argwhere(outline > 0)
    if found.size:
        center = (BOX // 2, BOX // 2)
        onTarget, outlineHits = checkInOutline(outline, center)
        if onTarget:
            distances = [sqrt((x-center[0])**2 + (y-center[1])**2) for _, (x, y) in outlineHits]
            if sum(distances) / len(distances) >= 3:
                return center, outline

    return None, outline

def checkInOutline(mask, center):
    directions = [(0, -1), (-1, 0), (1, 0)]  # up, left, right
    hits, outlineHits = 0, []
    for dx, dy in directions:
        x, y = center
        while 0 <= x < BOX and 0 <= y < BOX:
            if mask[y, x] > 0:
                outlineHits.append((center, (x, y)))
                hits += 1
                break
            x += dx; y += dy
    return hits == 3, outlineHits

class Debug:
    def __init__(self):
        self.window = tk.Tk()
        self.window.attributes("-type", "dialog")
        self.canvas = tk.Canvas(self.window, width=BOX, height=BOX, bg="black")
        self.canvas.pack()

    def update(self, target, mask):
        photo = PhotoImage(image=Image.fromarray(mask))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo

        self.canvas.create_line(BOX//2, 0, BOX//2, BOX, fill="gray", dash=(2, 2))
        self.canvas.create_line(0, BOX//2, BOX, BOX//2, fill="gray", dash=(2, 2))

        if target:
            x, y = target
            self.canvas.create_oval(x-5, y-5, x+5, y+5, outline="white")
            self.canvas.create_line(x, 0, x, BOX, fill="yellow")
            self.canvas.create_line(0, y, BOX, y, fill="yellow")
            self.canvas.create_text(10, 10, anchor=tk.NW, text=f"({x}, {y})", fill="yellow")

        for x, y, w, h in bBoxes:
            self.canvas.create_rectangle(x, y, x+w, y+h, outline="red", width=2)

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