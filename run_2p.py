import stage_control
import Gamepad
import time

import flask
import threading

###################################################
# DEFINE STAGE VARIABLES
###################################################
stages = [
    stage_control.ESP300StageControl(
        "/dev/serial/by-path/pci-0000:00:14.0-usb-0:1.3:1.0-port0", 19200, 1
    ),
]
###################################################

###################################################
# DEFINE GAMEPAD VARIABLES
###################################################
gamepadType = Gamepad.Xbox360

deadzone = 0.01
right_invert = {"X": False, "Y": True}
right_channel_map = {"X": "X", "Y": "Y"}
right_velocity_max = 20
right_velocity_scale = 100

z_velocity_max = 0.4

gamepad_disable = False
###################################################

###################################################
# FLASK API
###################################################
CHANNEL_COUNT = 3
channel_map = {"X": (stages[0], 1), "Y": (stages[0], 2), "Z": (stages[0], 3)}

flask_app = flask.Flask("FLASK_API")


@flask_app.route("/")
def hello_world():
    return "Server up."


@flask_app.route("/disable_gamepad")
def disable_gamepad():
    global gamepad_disable
    gamepad_disable = True
    return "Done."


@flask_app.route("/enable_gamepad")
def enable_gamepad():
    global gamepad_disable
    gamepad_disable = False
    return "Done."


@flask_app.route("/move/<ax>/<loc>")
def move(ax, loc):
    ax, loc = int(ax), float(loc)
    channel_map[ax][0].send_move(channel_map[ax][1], loc)
    return "Done."


@flask_app.route("/velocity/<ax>/<speed>")
def velocity(ax, speed):
    ax, speed = int(ax), float(speed)
    channel_map[ax][0].send_velocity(channel_map[ax][1], speed)
    return "Done."


@flask_app.route("/is_moving")
def is_moving():
    return {"is_moving": any(s.get_is_moving()[c] for s, c in channel_map.values())}


@flask_app.route("/get_is_moving")
def get_moving():
    return {cid: s.get_is_moving()[c] for cid, (s, c) in channel_map.items()}


@flask_app.route("/get_positions")
def get_positions():
    return {cid: s.get_current_position()[c] for cid, (s, c) in channel_map.items()}


@flask_app.route("/emergency_stop")
def emergency_stop():
    for stage in stages:
        stage.emergency_stop()
    return "Done."


ft = threading.Thread(
    target=lambda: flask_app.run(
        port=5000, debug=True, use_reloader=False, host="0.0.0.0"
    )
)

ft.start()
###################################################

###################################################
# GAMEPAD LOOP
###################################################
while True:
    print("Please connect your gamepad...")
    while not Gamepad.available():
        time.sleep(1.0)
    gamepad = gamepadType()
    print("Gamepad connected")

    while gamepad.isConnected():
        eventType, control, value = gamepad.getNextEvent()

        if gamepad_disable:
            continue

        if eventType == "AXIS":
            if control == 6 or control == 7:  # z-axis
                # 6 == dpad horizontal; 7 == dpad vertical
                ax, i = channel_map["Z"]
                if abs(value) < deadzone:  # eps
                    ax.stop(i)
                else:
                    value *= -1 if (control == 7) else 1
                    direction = "+" if value > 0 else "-"
                    velocity = (
                        z_velocity_max if (control == 6) else (z_velocity_max / 10)
                    )

                    ax.send_velocity(i, velocity)
                    ax.send_move_indefinite(i, direction)
            elif control == "LT":
                pass
            elif control == "RT":
                pass
            elif control.startswith("RIGHT-") or control.startswith("LEFT-"):
                is_left = control.startswith("LEFT")
                ax = control.split('-')[1]
                ax = right_channel_map[ax]
                ax, i = channel_map[ax]

                if abs(value) < deadzone:
                    stages[0].stop(ax)
                    # print("Stopping Axis")
                else:
                    value *= right_velocity_scale * right_velocity_max / 100.0
                    value *= 0.04 if is_left else 1.0
                    value *= -1 if right_invert[ax] else 1

                    direction = "+" if (value > 0) else "-"

                    stages[0].send_velocity(ax, abs(value))
                    stages[0].send_move_indefinite(ax, direction)
                    # print("New Velocity:", velocity)
            else:
                print(eventType, control, value)

        if eventType == "BUTTON":
            if value:
                match control:
                    case "Y":
                        for ax, i in channel_map.values():
                            ax.send_enable_axis(i)
                    case "X":
                        for ax, i in channel_map.values():
                            ax.stop(i)
                    case "B":
                        right_velocity_scale -= 20
                        if right_velocity_scale == 0:
                            right_velocity_scale = 100
                        print("Scaling", right_velocity_scale)
                    case "A":
                        pass
                    case "RB":
                        ax, i = channel_map["Z"]
                        ax.stop(i)
                        ax.send_velocity(i, z_velocity_max)
                        ax.home(i)
                    case "LB":
                        for c in ["X", "Y"]:
                            ax, i = channel_map[c]
                            ax.stop(i)
                            ax.send_velocity(i, right_velocity_max)
                            ax.home(i)
                    case "START":
                        pass
            else:
                pass

    gamepad.disconnect()
