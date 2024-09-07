# pyright: reportAttributeAccessIssue=false
from evdev import ecodes, UInput
from time import sleep
import evdev
import select

SENS = ?  # In-game sensitivity

def findMouse():
    return next((device for device in map(evdev.InputDevice, evdev.list_devices())
                if "pointer" in device.name.lower()), None)

def move(ui, start_x, start_y, end_x, end_y, steps=?):
    x, y = int((end_x - start_x) * SENS/15), int((end_y - start_y) * SENS/15)
    x_i = y_i = 0

    for i in range(1, steps + 1):
        to_x, to_y = int((x * i) / steps), int((y * i) / steps)
        dx, dy = to_x - x_i, to_y - y_i

        if dx != 0:
            ui.write(ecodes.EV_REL, ecodes.REL_X, dx)
            x_i += dx
        if dy != 0:
            ui.write(ecodes.EV_REL, ecodes.REL_Y, dy)
            y_i += dy

        ui.syn()
        sleep(0.001)

def inputLoop(ui, mouse, getTarget, center):
    while True:
        r, w, x = select.select([mouse.fd], [], [], 0.01)
        if r:
            for event in mouse.read():
                if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_LEFT:
                    if event.value == 1:  # press
                        target = getTarget()
                        if target: move(ui, center, center, target[0], target[1])
                    ui.write(ecodes.EV_KEY, ecodes.BTN_LEFT, event.value)
                else:
                    ui.write_event(event)
                ui.syn()

class MouseHandler:
    def __init__(self, center):
        self.center = center
        self.mouse = findMouse()
        if not self.mouse:
            raise RuntimeError("Mouse not found")
        
        self.mouse.grab()
        
        self.cap = {
            ecodes.EV_KEY: [ecodes.BTN_LEFT, ecodes.BTN_RIGHT, ecodes.BTN_MIDDLE, ecodes.BTN_SIDE, ecodes.BTN_EXTRA],
            ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL],
        }
        self.ui = UInput(self.cap, name="virtual-mouse")

    def start(self, target):
        inputLoop(self.ui, self.mouse, target, self.center)

    def cleanup(self):
        self.mouse.ungrab()
        self.ui.close()