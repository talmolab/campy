"""

"""

from campy.cameras import unicam
import os
import time
import logging
import sys
import numpy as np
from collections import deque
import csv
import imageio
import cv2


def LoadSystem(params):

    return params["cameraMake"]


def GetDeviceList(system):

    return system


def LoadDevice(systems, params, cam_params):

    return cam_params


def GetSerialNumber(device):

    return "MiniCAMv1"


def GetModelName(camera):

    return "MiniCAMv1"


def OpenCamera(cam_params):

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_FFMPEG
    camera = cv2.VideoCapture(cam_params["cameraSelection"], backend)
    print(f"Opened camera ID: {cam_params['cameraSelection']}")

    cam_params["cameraModel"] = "MiniCAMv1"

    cam_params = LoadSettings(cam_params, camera)
    return camera, cam_params


def LoadSettings(cam_params, camera):

    # Set camera parameters.
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, cam_params["frameWidth"])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_params["frameHeight"])

    return cam_params


def StartGrabbing(camera):

    return True


def GrabFrame(camera, frameNumber):

    success, img = camera.read()
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # BGR -> RGB
    return img


def GetImageArray(grabResult):

    return grabResult


def GetTimeStamp(grabResult):

    return time.perf_counter()


def DisplayImage(cam_params, dispQueue, grabResult):
    # Downsample image
    img = grabResult[
        :: cam_params["displayDownsample"], :: cam_params["displayDownsample"], :
    ]

    # Send to display queue
    dispQueue.append(img)


def ReleaseFrame(grabResult):

    del grabResult


def CloseCamera(cam_params, camera):

    print("Closing {}... Please wait.".format(cam_params["cameraName"]))
    # Close camera after acquisition stops
    del camera


def CloseSystem(system, device_list):
    del system
    del device_list
