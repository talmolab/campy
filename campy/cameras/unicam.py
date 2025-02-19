"""
Unicam unifies camera APIs with common syntax to simplify multi-camera acquisition and 
reduce redundancy in campy code.
"""

import os, sys, time, csv, logging
import numpy as np
from collections import deque
from scipy import io as sio
from rich.pretty import pprint
from rich.console import Console
from datetime import timedelta
import traceback


console = Console()


def ImportCam(make):
    if make == "basler":
        from campy.cameras import basler as cam
    elif make == "flir":
        from campy.cameras import flir as cam
    elif make == "emu":
        from campy.cameras import emu as cam
    elif make == "opencv":
        from campy.cameras import opencv as cam
    elif make == "minicam":
        from campy.cameras import minicam as cam
    else:
        print("Camera make is not supported by CamPy. Check config.", flush=True)
    return cam


def LoadSystems(params):
    try:
        systems = {}
        makes = GetMakeList(params)
        for m in range(len(makes)):
            systems[makes[m]] = {}
            cam = ImportCam(makes[m])
            systems[makes[m]]["system"] = cam.LoadSystem(params)
    except Exception as e:
        console.log(
            "Caught exception at camera/unicam.py LoadSystems. "
            "Check cameraMake:\n" + traceback.format_exc()
        )
        raise
    return systems


def LoadDevice(systems, params, cam_params):
    try:
        cam = ImportCam(cam_params["cameraMake"])
        cam_params = cam.LoadDevice(systems, params, cam_params)
    except Exception as e:
        console.log(
            "Caught exception at camera/unicam.py LoadDevice. "
            "Check cameraMake:\n" + traceback.format_exc()
        )
        raise
    return cam_params


def OpenCamera(cam_params, stopWriteQueue):
    # Import the cam module
    cam = ImportCam(cam_params["cameraMake"])

    try:
        camera, cam_params = cam.OpenCamera(cam_params)

        print(
            "Opened {}: {} {} serial# {}".format(
                cam_params["cameraName"],
                cam_params["cameraMake"],
                cam_params["cameraModel"],
                cam_params["cameraSerialNo"],
            )
        )

    except Exception as e:
        console.log(
            "Caught error at cameras/unicam.py OpenCamera:\n" + traceback.format_exc()
        )
        stopWriteQueue.append("STOP")

    return cam, camera, cam_params


def GetDeviceList(systems, params):
    makes = GetMakeList(params)
    for m in range(len(makes)):
        cam = ImportCam(makes[m])
        system = systems[makes[m]]["system"]
        deviceList = cam.GetDeviceList(system)
        serials = [cam.GetSerialNumber(deviceList[i]) for i in range(len(deviceList))]
        systems[makes[m]]["serials"] = serials
        systems[makes[m]]["deviceList"] = deviceList
    return systems


def GetMakeList(params):
    if type(params["cameraMake"]) is list:
        cameraMakes = [
            params["cameraMake"][m] for m in range(len(params["cameraMake"]))
        ]
    elif type(params["cameraMake"]) is str:
        cameraMakes = [params["cameraMake"]]
    makes = list(set(cameraMakes))
    return makes


def GrabData(cam_params):
    grabdata = {}
    grabdata["timeStamp"] = []
    grabdata["frameNumber"] = []
    grabdata["cameraName"] = cam_params["cameraName"]

    # Calculate display rate
    if cam_params["displayFrameRate"] <= 0:
        grabdata["frameRatio"] = float("inf")
    elif (
        cam_params["displayFrameRate"] > 0
        and cam_params["displayFrameRate"] <= cam_params["frameRate"]
    ):
        grabdata["frameRatio"] = int(
            round(cam_params["frameRate"] / cam_params["displayFrameRate"])
        )
    else:
        grabdata["frameRatio"] = cam_params["frameRate"]

    # Calculate number of images and chunk length
    grabdata["numImagesToGrab"] = int(
        round(cam_params["recTimeInSec"] * cam_params["frameRate"])
    )
    grabdata["chunkLengthInFrames"] = int(
        round(cam_params["chunkLengthInSec"] * cam_params["frameRate"])
    )

    return grabdata


def StartGrabbing(camera, cam_params, cam):
    grabbing = cam.StartGrabbing(camera)
    if grabbing:
        print(cam_params["cameraName"], "ready to trigger.")
    return grabbing


def CountFPS(grabdata, frameNumber, timeStamp):
    if frameNumber % grabdata["chunkLengthInFrames"] == 0:
        elapsed = timeStamp - grabdata["timeStamp"][0]
        elapsed_min, elapsed_sec = divmod(elapsed, 60)
        elapsed_hour, elapsed_min = divmod(elapsed_min, 60)

        frame_count = len(grabdata["timeStamp"])

        ts = grabdata["timeStamp"]
        if len(ts) > grabdata["chunkLengthInFrames"]:
            ts = ts[-grabdata["chunkLengthInFrames"] :]
        dts = np.abs(np.diff(ts))
        fps = 1 / dts
        fps_avg = fps.mean()
        fps_std = fps.std()

        sep = " [grey70]|[/grey70] "
        console.log(
            "".join(
                [
                    f"[bold]{grabdata['cameraName']}[/bold]",
                    sep,
                    "[bold]Session:[/bold] ",
                    f"{int(elapsed_hour):02}:{int(elapsed_min):02}:{int(elapsed_sec):02}",
                    sep,
                    f"[bold]Frames:[/bold] {frame_count:,}",
                    sep,
                    f"[bold]FPS:[/bold] {fps_avg:.1f} +- {fps_std:.1f}",
                ]
            )
        )


def GrabFrames(cam_params, writeQueue, dispQueue, stopReadQueue, stopWriteQueue):
    # Open the camera object
    cam, camera, cam_params = OpenCamera(cam_params, stopWriteQueue)

    console.log("Camera parameters:")
    pprint(cam_params)
    print()

    # Use Basler's default display window on Windows. Not supported on Linux
    if sys.platform == "win32" and cam_params["cameraMake"] == "basler":
        dispQueue = cam.OpenPylonImageWindow(cam_params)

    # Create dictionary for appending frame number and timestamp information
    grabdata = GrabData(cam_params)

    # Start grabbing frames from the camera
    grabbing = StartGrabbing(camera, cam_params, cam)

    frameNumber = 0
    firstTimeStamp = None
    while not stopReadQueue:
        try:
            # Grab image from camera buffer if available
            grabResult = cam.GrabFrame(camera, frameNumber)
            img = cam.GetImageArray(grabResult)

            # Append timeStamp and frameNumber to grabdata
            frameNumber += 1
            grabdata["frameNumber"].append(frameNumber)  # first frame = 1
            timeStamp = cam.GetTimeStamp(grabResult)
            grabdata["timeStamp"].append(timeStamp)
            if firstTimeStamp is None:
                firstTimeStamp = timeStamp

            # Append numpy array to writeQueue for writer to append to file
            writeQueue.append((frameNumber, timeStamp, img))

            # Display converted, downsampled image in the Window
            if frameNumber % grabdata["frameRatio"] == 0:
                img = cam.DisplayImage(cam_params, dispQueue, grabResult)

            CountFPS(grabdata, frameNumber, timeStamp)

            cam.ReleaseFrame(grabResult)

            if (frameNumber >= grabdata["numImagesToGrab"]) or (
                (timeStamp - firstTimeStamp) >= cam_params["recTimeInSec"]
            ):
                break

        except Exception as e:
            if cam_params["cameraDebug"]:
                console.log(
                    "Caught exception at cameras/unicam.py GrabFrames:\n"
                    + traceback.format_exc()
                )
            time.sleep(0.001)

    # Close the camaera, save metadata, and tell writer and display to close
    cam.CloseCamera(cam_params, camera)
    SaveMetadata(cam_params, grabdata)
    if not sys.platform == "win32" or not cam_params["cameraMake"] == "basler":
        dispQueue.append("STOP")
    stopWriteQueue.append("STOP")


def SaveMetadata(cam_params, grabdata):
    full_folder_name = os.path.join(cam_params["videoFolder"], cam_params["cameraName"])

    try:
        # Zero timeStamps
        timeFirstGrab = grabdata["timeStamp"][0]
        grabdata["timeStamp"] = [i - timeFirstGrab for i in grabdata["timeStamp"]]

        # Get the frame and time counts to save into metadata
        frame_count = grabdata["frameNumber"][-1]
        time_count = grabdata["timeStamp"][-1]
        fps_count = frame_count / time_count
        console.log(
            f"Camera {cam_params['cameraName']} saved {frame_count} "
            f"frames at {fps_count} fps."
        )

        meta = cam_params

        # Save frame data to numpy file
        npy_filename = os.path.join(full_folder_name, "frametimes.npy")
        x = np.array([grabdata["frameNumber"], grabdata["timeStamp"]])
        np.save(npy_filename, x)

        # Also save frame data to MATLAB file
        mat_filename = os.path.join(full_folder_name, "frametimes.mat")
        matdata = {}
        matdata["frameNumber"] = grabdata["frameNumber"]
        matdata["timeStamp"] = grabdata["timeStamp"]
        sio.savemat(mat_filename, matdata, do_compression=True)

        # Save parameters and recording metadata to csv spreadsheet
        csv_filename = os.path.join(full_folder_name, "metadata.csv")
        meta["totalFrames"] = grabdata["frameNumber"][-1]
        meta["totalTime"] = grabdata["timeStamp"][-1]

        with open(csv_filename, "w", newline="") as f:
            w = csv.writer(f, delimiter=",", quoting=csv.QUOTE_ALL)
            for row in meta.items():
                # Print items that are not objects or dicts
                if isinstance(row[1], (list, str, int, float)):
                    w.writerow(row)

        console.log("Saved metadata for", cam_params["cameraName"])

    except Exception as e:
        console.log("Caught exception:\n" + traceback.format_exc())


def CloseSystems(systems, params):
    console.log("Closing systems...")
    makes = GetMakeList(params)
    for m in range(len(makes)):
        cam = ImportCam(makes[m])
        cam.CloseSystem(systems[makes[m]]["system"], systems[makes[m]]["deviceList"])
    console.log("Exiting campy...")
