CD C:\code\campy
SET log_date=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%
SET log_file=%cd%\recording_logs.%log_date%.txt
CALL  C:\Miniconda3\Scripts\activate.bat "C:\Miniconda3\envs\campy"
rem campy-acquire configs\campy_config_4cam_minicam.4xGPU.yaml > %log_file%
campy-acquire configs\campy_config_3cam_minicam.GPU.yaml > %log_file%