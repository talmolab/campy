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


def LoadDevice(cam_params):

    return cam_params["device"]


def GetSerialNumber(device):

    return device


def GetModelName(camera):

    return "Emulated_Camera"


def OpenCamera(cam_params, device):

    backend = cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_FFMPEG
    camera = cv2.VideoCapture(cam_params["camera"], backend)

    # Set features manually or automatically, depending on configuration
    # frame_size = camera.get_meta_data()["size"]
    # cam_params["frameWidth"] = frame_size[0]
    # cam_params["frameHeight"] = frame_size[1]

    cam_params = LoadSettings(cam_params, camera)
    print(f"Opened camera ID: {self.camera}.")
    return camera, cam_params


def LoadSettings(cam_params, camera):

    # Set camera parameters.
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, cam_params["frameWidth"])
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_params["frameHeight"])
    camera.set(cv2.CAP_PROP_BUFFERSIZE, cam_params["bufferSize"])
    # camera.set(cv2.CAP_PROP_BRIGHTNESS, self.camera_brightness)

    # Query camera for parameter values that actually took effect.
    cam_params["frameWidth"] = camera.get(cv2.CAP_PROP_FRAME_WIDTH)
    cam_params["frameHeight"] = camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
    cam_params["bufferSize"] = camera.get(cv2.CAP_PROP_BUFFERSIZE)

    return cam_params


def StartGrabbing(camera):

    return True


def GrabFrame(camera, frameNumber):

    success, img = camera.read()
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
