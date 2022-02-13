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

    return "OpenCV"


def GetModelName(camera):

    return "OpenCV camera"


def OpenCamera(cam_params):

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_FFMPEG
    camera = cv2.VideoCapture(cam_params["cameraSelection"], backend)

    cam_params["cameraModel"] = "OpenCV"

    cam_params = LoadSettings(cam_params, camera)
    print(f"Opened camera ID: {cam_params['cameraSelection']}")
    return camera, cam_params


def LoadSettings(cam_params, camera):

    # Set camera parameters.
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, cam_params["frameWidth"])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_params["frameHeight"])
    camera.set(cv2.CAP_PROP_FPS, cam_params["frameRate"])
    camera.set(cv2.CAP_PROP_BUFFERSIZE, cam_params["bufferSize"])
    # camera.set(cv2.CAP_PROP_BRIGHTNESS, self.camera_brightness)

    if cam_params["opencvExposure"] > 0:
        camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    elif cam_params["opencvExposure"] < 0:
        camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
        camera.set(cv2.CAP_PROP_EXPOSURE, cam_params["opencvExposure"])

    # Query camera for parameter values that actually took effect.
    cam_params["frameRate"] = camera.get(cv2.CAP_PROP_FPS)
    cam_params["frameWidth"] = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
    cam_params["frameHeight"] = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cam_params["bufferSize"] = int(camera.get(cv2.CAP_PROP_BUFFERSIZE))
    cam_params["opencvExposure"] = camera.get(cv2.CAP_PROP_EXPOSURE)

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
