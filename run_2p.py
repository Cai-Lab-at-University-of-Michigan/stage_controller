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
right_channel_map = {"X": 1, "Y": 2}
right_velocity_max = 20
right_velocity_scale = 100

z_velocity_max = 0.4

gamepad_disable = False
###################################################

###################################################
# FLASK API
###################################################
CHANNEL_COUNT = 3
channel_map = {1: (stages[0], 0), 2: (stages[0], 1), 3: (stages[0], 2)}
axis_map = {"z": 1, "x": 2, "y": 3}

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
            if type(control) == int:
                if control == 7:
                    value *= -1
                if abs(value) < 0.01:  # eps
                    stages[1].stop(1)
                else:
                    direction = "+" if value > 0 else "-"
                    velocity = 0
                    if control == 7:
                        velocity = z_velocity_max
                    elif control == 6:
                        velocity = z_velocity_max / 10
                    stages[1].send_velocity(1, velocity)
                    stages[1].send_move_indefinite(1, direction)
                # 6 == dpad horizontal; 7 == dpad vertical
            elif control == "LT":
                pass
            elif control == "RT":
                pass
            elif control.startswith("RIGHT-") or control.startswith("LEFT-"):
                left = "LEFT" in control
                ax = control.replace("RIGHT-", "").replace("LEFT-", "")
                value *= -1 if right_invert[ax] else 1
                ax = right_channel_map[ax]

                if abs(value) < deadzone:
                    stages[0].stop(ax)
                    # print("Stopping Axis")
                else:
                    velocity = right_velocity_scale * right_velocity_max * value / 100
                    velocity *= 0.04 if left else 1.0
                    direction = "+" if (velocity > 0) else "-"
                    velocity = abs(velocity)

                    stages[0].send_velocity(ax, velocity)
                    stages[0].send_move_indefinite(ax, direction)
                    # print("New Velocity:", velocity)
            else:
                print(eventType, control, value)
        if eventType == "BUTTON":
            if value:
                if control == "Y":
                    for ax in right_channel_map.values():
                        stages[0].send_enable_axis(0)
                elif control == "X":
                    stages[0].stop(1)
                    stages[0].stop(2)
                    stages[1].stop(1)
                elif control == "B":
                    right_velocity_scale -= 20
                    if right_velocity_scale == 0:
                        right_velocity_scale = 100
                    print("Scaling", right_velocity_scale)
                elif control == "A":
                    pass
                elif control == "RB":
                    for ax in right_channel_map.values():
                        stages[0].stop(ax)
                        stages[0].send_velocity(ax, right_velocity_max)
                        stages[0].home(ax)
                elif control == "LB":
                    stages[1].stop(1)
                    stages[1].send_velocity(1, z_velocity_max)
                    stages[1].home(1)
                elif control == "START":
                    pass
                else:
                    print(eventType, control, value)
            else:
                pass

    gamepad.disconnect()
