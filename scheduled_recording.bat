SET log_file=%cd%\recording_logs.txt
call C:\Miniconda3\envs\campy\Scripts\activate.bat
campy-acquire configs\campy_config_4cam_minicam.4xGPU.yaml > %log_file%