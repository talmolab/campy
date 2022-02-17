"""
"""
from imageio_ffmpeg import write_frames
import os, time
from campy.utils.utils import QueueKeyboardInterrupt
from rich.console import Console
import traceback
from pathlib import Path
import csv
import json


console = Console()


def OpenMetadataWriter(folder_name, cam_params, flush_every=500):

    # Save metadata
    cam_params_path = (Path(folder_name) / "cam_params.csv").as_posix()
    with open(cam_params_path, "w") as f:
        json.dump(cam_params, f)
    console.log("Saved camera params to: " + cam_params_path)

    # Setup timestamp streamer
    ts_path = (Path(folder_name) / "timestamps.csv").as_posix()
    console.log("Writing timestamps to: " + ts_path)
    if Path(ts_path).exists():
        Path(ts_path).unlink()
    file = open(ts_path, "a")
    writer = csv.DictWriter(
        file, delimiter=",", fieldnames=["frameNumber", "timeStamp"]
    )
    writer.writeheader()
    t0 = None

    # Create a writer in a generator loop
    try:
        while True:
            frameNumber, timeStamp = yield  # this blocks until the .send() is called
            if t0 is None:
                t0 = timeStamp
            timeStamp -= t0
            writer.writerow({"frameNumber": frameNumber, "timeStamp": timeStamp})
            if frameNumber % flush_every == 0:
                file.flush()
    except:
        console.log(traceback.format_exc())
        raise
    finally:
        file.flush()
        file.close()
        console.log(f"Closed metadata writer for: {ts_path}")


def OpenWriter(cam_params, queue):
    try:
        writing = False
        folder_name = os.path.join(cam_params["videoFolder"], cam_params["cameraName"])
        file_name = cam_params["videoFilename"]
        full_file_name = os.path.join(folder_name, file_name)

        if not os.path.isdir(folder_name):
            os.makedirs(folder_name)
            print("Made directory {}.".format(folder_name))

        # Flip blue and red for flir camera input
        if (
            cam_params["pixelFormatInput"] == "bayer_bggr8"
            and cam_params["cameraMake"] == "flir"
        ):
            cam_params["pixelFormatInput"] == "bayer_rggb8"

        # Load encoding parameters from cam_params
        pix_fmt_out = cam_params["pixelFormatOutput"]
        codec = str(cam_params["codec"])
        quality = str(cam_params["quality"])
        preset = str(cam_params["preset"])
        frameRate = str(cam_params["frameRate"])
        gpuID = str(cam_params["gpuID"])

        # Load defaults
        output_params = []

        # CPU compression
        if cam_params["gpuID"] == -1:
            console.log(f"Opened: {full_file_name} using CPU to compress the stream.")
            if preset == "None":
                preset = "fast"
            output_params = [
                "-r:v",
                frameRate,
                "-preset",
                preset,
                "-tune",
                "fastdecode",
                "-crf",
                quality,
                "-bufsize",
                "20M",
                "-maxrate",
                "10M",
                "-bf:v",
                "4",
                "-vsync",
                "0",
            ]
            if pix_fmt_out == "rgb0" or pix_fmt_out == "bgr0":
                pix_fmt_out = "yuv420p"
            if cam_params["codec"] == "h264":
                codec = "libx264"
                output_params.append("-x264-params")
                output_params.append("nal-hrd=cbr")
            elif cam_params["codec"] == "h265":
                codec = "libx265"

        # GPU compression
        else:
            # Nvidia GPU (NVENC) encoder optimized parameters
            print(
                "Opened: {} using GPU {} to compress the stream.".format(
                    full_file_name, cam_params["gpuID"]
                )
            )
            if cam_params["gpuMake"] == "nvidia":
                if preset == "None":
                    preset = "fast"
                output_params = [
                    "-r:v",
                    frameRate,  # important to play nice with vsync "0"
                    "-preset",
                    preset,  # set to "fast", "llhp", or "llhq" for h264 or hevc
                    "-qp",
                    quality,
                    "-bf:v",
                    "0",
                    "-vsync",
                    "0",
                    "-2pass",
                    "0",
                    "-gpu",
                    gpuID,
                ]
                if cam_params["codec"] == "h264":
                    codec = "h264_nvenc"
                elif cam_params["codec"] == "h265":
                    codec = "hevc_nvenc"

            # AMD GPU (AMF/VCE) encoder optimized parameters
            elif cam_params["gpuMake"] == "amd":
                # Preset not supported by AMF
                output_params = [
                    "-r:v",
                    frameRate,
                    "-usage",
                    "lowlatency",
                    "-rc",
                    "cqp",  # constant quantization parameter
                    "-qp_i",
                    quality,
                    "-qp_p",
                    quality,
                    "-qp_b",
                    quality,
                    "-bf:v",
                    "0",
                    "-hwaccel",
                    "auto",
                    "-hwaccel_device",
                    gpuID,
                ]
                if pix_fmt_out == "rgb0" or pix_fmt_out == "bgr0":
                    pix_fmt_out = "yuv420p"
                if cam_params["codec"] == "h264":
                    codec = "h264_amf"
                elif cam_params["codec"] == "h265":
                    codec = "hevc_amf"

            # Intel iGPU encoder (Quick Sync) optimized parameters
            elif cam_params["gpuMake"] == "intel":
                if preset == "None":
                    preset = "faster"
                output_params = [
                    "-r:v",
                    frameRate,
                    "-bf:v",
                    "0",
                    "-preset",
                    preset,
                    "-q",
                    str(int(quality) + 1),
                ]
                if pix_fmt_out == "rgb0" or pix_fmt_out == "bgr0":
                    pix_fmt_out = "nv12"
                if cam_params["codec"] == "h264":
                    codec = "h264_qsv"
                elif cam_params["codec"] == "h265":
                    codec = "hevc_qsv"

        if cam_params["videoSegmentLengthInSec"] > 0:
            mins, secs = divmod(cam_params["videoSegmentLengthInSec"], 60)
            hours, mins = divmod(mins, 60)
            output_params.extend(
                [
                    "-segment_time",
                    f"{hours:02}:{mins:02}:{secs:02}",
                    "-f",
                    "segment",
                    "-reset_timestamps",
                    "1",
                ]
            )
            p = Path(full_file_name)
            full_file_name = p.with_suffix(".%05d" + p.suffix).as_posix()

    except Exception as e:
        console.log(
            f"Caught exception at writer.py OpenWriter:\n" + traceback.format_exc()
        )
        raise

    # Initialize writer object (imageio-ffmpeg)
    while True:
        try:
            console.log("Video writer output_params:\n" " ".join(output_params))
            writer = write_frames(
                full_file_name,
                [cam_params["frameWidth"], cam_params["frameHeight"]],  # size [W,H]
                fps=cam_params["frameRate"],
                quality=None,
                codec=codec,
                pix_fmt_in=cam_params[
                    "pixelFormatInput"
                ],  # "bayer_bggr8", "gray", "rgb24", "bgr0", "yuv420p"
                pix_fmt_out=pix_fmt_out,
                bitrate=None,
                ffmpeg_log_level=cam_params[
                    "ffmpegLogLevel"
                ],  # "warning", "quiet", "info"
                input_params=["-an"],  # "-an" no audio
                output_params=output_params,
            )
            writer.send(None)  # Initialize the generator
            writing = True
            break

        except Exception as e:
            console.log(
                "Caught exception at writer.py OpenWriter:\n" + traceback.format_exc()
            )
            raise

    # Initialize read queue object to signal interrupt
    readQueue = {}
    readQueue["queue"] = queue
    readQueue["message"] = "STOP"

    # Initialize metadata writer
    metadata_writer = OpenMetadataWriter(folder_name, cam_params)
    metadata_writer.send(None)  # Initialize the generator

    return writer, metadata_writer, writing, readQueue


def WriteFrames(cam_params, writeQueue, stopReadQueue, stopWriteQueue):
    # Start ffmpeg video writer
    video_writer, metadata_writer, writing, readQueue = OpenWriter(
        cam_params, stopReadQueue
    )

    with QueueKeyboardInterrupt(readQueue):
        # Write until interrupted and/or stop message received
        while writing:
            if writeQueue:
                frameNumber, timeStamp, img = writeQueue.popleft()
                video_writer.send(img)
                metadata_writer.send((frameNumber, timeStamp))
            else:
                # Once queue is depleted and grabber stops, then stop writing
                if stopWriteQueue:
                    writing = False
                # Otherwise continue writing
                time.sleep(0.01)

    # Close up...
    console.log(f"Closing video writer for {cam_params['cameraName']}. Please wait...")
    time.sleep(1)
    video_writer.close()
    metadata_writer.close()
