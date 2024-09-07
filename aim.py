from subprocess import getoutput as out, Popen as run, DEVNULL
import tkinter as tk
from PIL.ImageTk import PhotoImage
from PIL import Image
import numpy as num
from time import sleep
from threading import Thread
import cv2 as cv

TOL, BOX = ?, 400
NAME_HSV = (?, ?, ?)
OUTLINE_HSV = (?, ?, ?)
PADDING, MAX_DY = ?, ?

def getRes():
    for line in out("wlr-randr").split('\n'):
        if "current" in line: return map(int, line.split()[0].split('x'))

DEV = "/dev/video0"
W, H = getRes()

geom = f"{(W-BOX)//2},{(H-BOX)//2} {BOX}x{BOX}"
exe = out("which wl-screenrec")

rec = run(["sudo", "-E", exe, "-g", geom, "--ffmpeg-muxer", "v4l2", "-f", DEV], stdout=DEVNULL)

name_mask, outline_mask, bBoxes = None, None, []

def mask(hsv, vals, tol=TOL):
    lower = num.array([vals[0] - tol, vals[1], vals[2]])
    upper = num.array([vals[0] + tol, 255, 255])
    return cv.inRange(hsv, lower, upper)

def combineBoxes(boxes):
    if not boxes:
        return []

    boxes.sort(key=lambda box: (box[1], box[0]))  # sort by y, then x
    combined = []
    c = list(boxes[0])  # current box

    for n in boxes[1:]:  # next box
        if abs(c[1] - n[1]) <= MAX_DY and c[0] <= n[0] + n[2] and n[0] <= c[0] + c[2]:
            c[2] = max(c[0] + c[2], n[0] + n[2]) - c[0]
            c[3] = max(c[1] + c[3], n[1] + n[3]) - c[1]
        else:
            combined.append(tuple(c))
            c = list(n)

    combined.append(tuple(c))
    return combined

def process(frame):
    global bBoxes
    hsv = cv.cvtColor(frame, cv.COLOR_BGR2HSV)

    name_mask = mask(hsv, NAME_HSV)
    kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (8, 8))
    name_mask = cv.morphologyEx(cv.morphologyEx(name_mask, cv.MORPH_CLOSE, kernel), cv.MORPH_OPEN, kernel)
    outline_mask = mask(hsv, OUTLINE_HSV)

    bBoxes = []
    contours, _ = cv.findContours(name_mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        x, y, w, h = cv.boundingRect(contour)
        if (w / h) > 2 and cv.contourArea(contour) > 100:  # WIP
            # Add padding to the bounding box
            x, y = max(0, x - PADDING), max(0, y - PADDING)
            w, h = min(BOX - x, w + 2 * PADDING), min(BOX - y, h + 2 * PADDING)
            bBoxes.append((x, y, w, h))

    # Combine nearby boxes
    bBoxes = combineBoxes(bBoxes)

    return name_mask, outline_mask

def findTarget(outline_mask, left, bottom, right, bBoxes):
    height, width = outline_mask.shape
    top, min_dist = None, BOX

    for x in range(left, right + 1):
        for y in range(bottom, height):
            if y >= height or x >= width:
                break
            if outline_mask[y, x] > 0:
                # Ensure point isn't inside nametag bbox
                if not any(b[0] <= x < b[0]+b[2] and b[1] <= y < b[1]+b[3] for b in bBoxes):
                    distance = y - bottom
                    if distance < min_dist:
                        min_dist = distance
                        top = (x, y)
                    break

    return top

class Debug:
    def __init__(self):
        self.window = tk.Tk()
        self.window.attributes("-type", "dialog")
        self.canvas = tk.Canvas(self.window, width=BOX, height=BOX, bg="black")
        self.canvas.pack()

    def update(self, name_mask, outline_mask):
        composite = cv.cvtColor(name_mask, cv.COLOR_GRAY2RGB)
        composite[:,:,1] = cv.max(composite[:,:,1], outline_mask) # green channel

        photo = PhotoImage(image=Image.fromarray(composite))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self.canvas.image = photo

        self.canvas.create_line(BOX//2, 0, BOX//2, BOX, fill="gray", dash=(2, 2))
        self.canvas.create_line(0, BOX//2, BOX, BOX//2, fill="gray", dash=(2, 2))

        target, name_above = None, None
        min_dist, center = BOX, BOX // 2

        for x, y, w, h in bBoxes:
            self.canvas.create_rectangle(x, y, x+w, y+h, outline="red", width=2)
            bottom = y + h
            # Check if reticle is directly below this bounding box
            if x <= center <= x+w and center > bottom:
                distance = center - bottom
                if distance < min_dist:
                    min_dist = distance
                    name_above = (x, y, w, h)

        if name_above:
            x, y, w, h = name_above
            target = findTarget(outline_mask, x, y+h, x+w, bBoxes)

        if target:
            x, y = target
            self.canvas.create_oval(x-5, y-5, x+5, y+5, outline="yellow", width=2)
            self.canvas.create_text(10, 10, anchor=tk.NW, text=f"({x}, {y})", fill="yellow")
            self.canvas.create_line(center, center, x, y, fill="yellow", width=2)
        self.window.update()

def capture():
    global name_mask, outline_mask
    cap = cv.VideoCapture(DEV)
    if not cap.isOpened():
        raise IOError("ERROR: could not open video device.")
    while True:
        ret, frame = cap.read()
        if ret:
            name_mask, outline_mask = process(frame)
        sleep(0.01)

Thread(target=capture, daemon=True).start()
debug = Debug()

try:
    while True:
        if name_mask is not None: debug.update(name_mask, outline_mask)
except Exception as e: print(f"ERROR: {e}")
finally:
    debug.window.destroy()
    rec.terminate()