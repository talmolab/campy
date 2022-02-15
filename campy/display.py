"""

"""
import sys, time, logging, warnings
import numpy as np
import matplotlib as mpl
warnings.filterwarnings("ignore")
mpl.use('Qt5Agg') # ignore qtapp warning...
import matplotlib.pyplot as plt
import cv2


def DrawFigure(num, height, width, title):
	mpl.rcParams['toolbar'] = 'None' 

	figure = plt.figure(num)
	figure.canvas.manager.set_window_title(title)
	ax = plt.axes([0,0,1,1], frameon=False)

	plt.axis('off')
	plt.autoscale(tight=True)
	plt.ion()

	imageWindow = ax.imshow(np.zeros((height, width, 3), dtype='uint8'), interpolation='none')

	figure.canvas.draw()
	plt.show(block=False)

	return figure, imageWindow


def DisplayFrames(cam_params, dispQueue):
	n_cam = cam_params['n_cam']
	
	if sys.platform == "win32" and cam_params['cameraMake'] == 'basler':
		# Display on Basler cameras uses the Pylon image window handled by cameras/basler.py
		pass
	else:
		figure, imageWindow = DrawFigure(n_cam+1, cam_params["frameHeight"], cam_params["frameWidth"], cam_params["cameraName"])
		while(True):
			try:
				if dispQueue:
					img = dispQueue.popleft()
					try:
						# imageWindow.set_data(img.squeeze())
						imageWindow.set_data(cv2.cvtColor(img, cv2.COLOR_GRAY2RGB))
						figure.canvas.draw()
						figure.canvas.flush_events()
					except Exception as e:
						# logging.exception('Caught exception at display.py DisplayFrames:')
						pass
				else:
					time.sleep(0.01)
			except KeyboardInterrupt:
				break
		plt.close(figure)