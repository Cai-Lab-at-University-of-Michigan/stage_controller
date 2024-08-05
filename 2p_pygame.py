import serial
import pygame

from pygame.locals import *

ser = serial.Serial("COM7", 19200, timeout=1, parity=serial.PARITY_NONE, rtscts=1)


def enable_axis(ax):
    cmd = f"{ax}MO\r\n"
    ser.write(bytes(cmd, "ascii"))


def stop_axis(ax):
    cmd = f"{ax}ST\r\n"
    ser.write(bytes(cmd, "ascii"))


def set_velocity(ax, vel):
    cmd = f"{ax}VA{vel}\r\n"
    ser.write(bytes(cmd, "ascii"))


def move_indef(axis, direction):
    cmd = f"{axis}MV{direction}\r\n"
    ser.write(bytes(cmd, "ascii"))


def read_error():
    cmd = f"TB\r\n"
    ser.write(bytes(cmd, "ascii"))
    return ser.readline()


def home_stage(axis):
    cmd = f"{axis}OR\r\n"
    ser.write(bytes(cmd, "ascii"))


def reset_stage():
    ser.write(bytes("RS\r\n", "ascii"))


pygame.init()
pygame.event.set_blocked((MOUSEMOTION, MOUSEBUTTONUP, MOUSEBUTTONDOWN))

pygame.joystick.init()

axes_map = {"x": 3, "y": 2, "z": 1}

for k, v in list(axes_map.items()):
    axes_map[k.upper()] = v

joystick = pygame.joystick.Joystick(0)
print(joystick.get_name())

while True:
    for event in pygame.event.get():
        if event.type == JOYAXISMOTION:
            # print(event.joy, event.axis, event.value)
            if event.axis >= 4:  # ignore triggers
                continue

            v = float(event.value)
            v *= 0.3

            direction = v > 0
            v = abs(v)

            match event.axis:
                case 0:  # LEFT-X
                    ax = axes_map["x"]
                case 1:  # LEFT-Y
                    ax = axes_map["y"]
                case 2:  # RIGHT-X
                    ax = axes_map["x"]
                case 3:  # RIGHT-Y
                    ax = axes_map["y"]
                case _:
                    continue

            if ax == axes_map["x"]:
                direction = direction
            elif ax == axes_map["y"]:
                direction = direction

            if event.axis == 0 or event.axis == 1:
                v *= 0.5

            if v < 0.1:
                stop_axis(ax)
            else:
                set_velocity(ax, v)
                move_indef(ax, "+" if direction else "-")

        if event.type == JOYHATMOTION:
            jh = tuple(i * 0.3 for i in event.value)

            v = 0
            v += float(jh[0])
            v += 0.5 * float(jh[1])

            direction = v > 0
            v = abs(v)

            ax = axes_map["z"]

            if v < 0.1:
                stop_axis(ax)
            else:
                set_velocity(ax, v)
                move_indef(ax, "+" if direction else "-")

        if event.type == JOYBUTTONDOWN:
            match event.button:
                case 0:  # A
                    pass
                case 1:  # B
                    print(read_error().strip().decode("ascii"))
                case 2:  # X
                    for i in range(3):
                        stop_axis(i + 1)
                case 3:  # Y
                    for i in range(1, 4):
                        enable_axis(i)
                case 4:  # LB
                    home_stage(axes_map["x"])
                    home_stage(axes_map["y"])
                case 5:  # RB
                    home_stage(axes_map["z"])
                case 6:  # BACK
                    pass
                case 7:  # start
                    reset_stage()
                case 8 | 9:  # JOY CLICKs, don't use
                    pass
                case _:
                    print("Unknown Button", event.button)
