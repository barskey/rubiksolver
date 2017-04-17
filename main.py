from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.graphics import *
#from kivy.uix.button import Button
from kivy.uix.image import Image as KvImage
#from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.behaviors import DragBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition

import rscube
import ConfigParser
from PIL import Image as PILImage
import time

Config.set('graphics', 'width', '480')
Config.set('graphics', 'height', '320')

CONFIGFILE = 'calibrate.txt'
config = ConfigParser.ConfigParser()

SCREEN_SIZE_X = 480 # hard coded for convenience
SCREEN_SIZE_Y = 320 # hard coded for convenience
IMG_SIZE_X = 320 # size of image in x to capture from camera
IMG_SIZE_Y = 240 # side of image in y to capture from camera
TAB_SIZE = 48 # hard coded for height of tab header plus 4-pixel border on both sides

class RubikSolver(BoxLayout):
	pass

class MainMenu(Screen):
	pass

class DragBox(DragBehavior, Label):
	pass

class SiteBox(DragBehavior, Label):

	def on_pos(self, *args):
		app = App.get_running_app()
		app.update_config('Sites', self.id + '_x', app.get_PIL_pos(self.x, 'x', self.width, app.crop_config['size']))
		app.update_config('Sites', self.id + '_y', app.get_PIL_pos(self.y, 'y', self.width, app.crop_config['size']))

class Settings(Screen):
	kim_crop = None
	kim_sites = None

	def add_crop_img(self):
		if self.kim_crop:
			self.ids.crop_float.remove_widget(self.kim_crop) # remove existing image if it exists

		# TODO change this to get actual image from camera
		self.kim_crop = KvImage(size=(IMG_SIZE_X, IMG_SIZE_Y), source='testimg\\uface.jpg')

		self.ids.crop_float.add_widget(self.kim_crop, 1)

	def add_sites_img(self):
		if self.kim_sites:
			self.ids.sites_float.remove_widget(self.kim_sites) # remove existing image if it exists

		# TODO change this to get actual image from camera
		# load/grab image
		pil = PILImage.open('testimg\\uface.jpg')

		# flip the image vertically so the y coords are bottom-up for kivy instead of top-down for PIL
		flip = pil.transpose(PILImage.FLIP_TOP_BOTTOM)

		# crop image and save to temp file (0,0 is in upper-left)
		size = App.get_running_app().crop_config['size']
		center_x = App.get_running_app().crop_config['center_x']
		center_y = App.get_running_app().crop_config['center_y']
		l = center_x - size / 2
		t = center_y - size / 2
		r = l + size
		b = t + size
		tmp = flip.crop((l, t, r, b))

		# flip it back
		tmp_img = tmp.transpose(PILImage.FLIP_TOP_BOTTOM)

		tmp_img.save('tmp.jpg', "JPEG") # TODO should this extension be hard coded?
		time.sleep(0.5) # DEBUG give it time to save the image

		self.kim_sites = KvImage(size=(size, size), source='tmp.jpg')

		if self.kim_sites:
			self.ids.sites_float.add_widget(self.kim_sites)

	def add_sites_boxes(self):

		app = App.get_running_app()
		site_config = app.site_config
		size = site_config['size']

		for i in xrange(1, 10):
			site_name = 'center' + str(i)

			x = app.get_screen_pos(site_config[site_name]['x'], 'x', size, app.crop_config['size'])
			y = app.get_screen_pos(site_config[site_name]['y'], 'y', size, app.crop_config['size'])

			box = SiteBox(id=site_name)

			self.ids.sites_float.add_widget(box)

			box.width = self.ids.site_slider.value
			box.height = self.ids.site_slider.value
			box.pos = (x, y)
			box.name = site_name

class RubikSolverApp(App):

	grip_a_config = {}
	grip_b_config = {}
	twist_a_config = {}
	twist_b_config = {}
	crop_config = {}
	site_config = {}

	def build(self):
		self.get_config()

		self.mycube = rscube.MyCube(self.site_config, self.crop_config, self.grip_a_config, self.twist_a_config, self.grip_b_config, self.twist_b_config)

		self.imgx = IMG_SIZE_X
		self.imgy = IMG_SIZE_Y

		self.sm = ScreenManager()
		self.sm.add_widget(MainMenu(name='home'))
		self.sm.add_widget(Settings(name='settings'))

		rs = RubikSolver()
		rs.add_widget(self.sm)

		Window.size = (SCREEN_SIZE_X, SCREEN_SIZE_Y) # debug for Windows/Mac
		

		return rs

	def go_screen(self, screen, dir):
		if dir == 'None':
			self.sm.transition = NoTransition()
		else:
			self.sm.transition = SlideTransition()
			self.sm.transition.direction = dir
		self.sm.current = screen

	def get_config(self):
		config.read(CONFIGFILE)

		for option in config.options('Crop'):
			self.crop_config[option] = config.getint('Crop', option)

		for option in config.options('GripA'):
			self.grip_a_config[option] = config.getint('GripA', option)

		for option in config.options('GripB'):
			self.grip_b_config[option] = config.getint('GripB', option)

		for option in config.options('TwistA'):
			self.twist_a_config[option] = config.getint('TwistA', option)

		for option in config.options('TwistB'):
			self.twist_b_config[option] = config.getint('TwistB', option)

		self.site_config['size'] = config.getint('Sites', 'size')

		for i in xrange(1, 10):
			configname_x = 'center' + str(i) + '_x'
			configname_y = 'center' + str(i) + '_y'
			x = config.getint('Sites', configname_x)
			y = config.getint('Sites', configname_y)
			self.site_config['center' + str(i)] = {'x': x, 'y': y}

	def update_config(self, setting, option, value):
		# TODO move gripper

		config.set(setting, option, str(int(value)))
		with open(CONFIGFILE, 'wb') as configfile:
			config.write(configfile)
		self.get_config()

	def exit_config(self):
		self.go_screen('home', 'left')

	"""
	transposes PIL coord from center to ll corner, then to screen coords
	return wrt 0,0 in ll of screen
	"""
	def get_screen_pos(self, coord, dir, box_size, img_size):
		if dir == 'x':
			ll_x = coord - box_size / 2 # move coord to ll corner in x
			offset_x = ll_x + (SCREEN_SIZE_X - img_size) / 2 # add to account for screen space to left of img
			return offset_x
		elif dir == 'y':
			ll_y = coord + box_size / 2 # move coord to ll corner in y
			transpose_y = img_size - ll_y # flip the coord so we are in bot-top for screen coords
			offset_y = transpose_y + (SCREEN_SIZE_Y - TAB_SIZE - img_size) / 2 # add screen space below img
			return offset_y

	"""
	transposes screen coord from ll corner to center, then to PIL coords
	return wrt 0,0 in ul of screen
	"""
	def get_PIL_pos(self, coord, dir, box_size, img_size):
		if dir == 'x':
			center_x = coord + box_size / 2 # center the coord
			offset_x = center_x - (SCREEN_SIZE_X - img_size) / 2 # subtract screen space to left of img
			return offset_x
		elif dir == 'y':
			center_y = coord + box_size / 2 # center the coord
			offset_y = center_y - (SCREEN_SIZE_Y - TAB_SIZE- img_size) / 2 # subtract screen space below img
			transpose_y = img_size - offset_y # flip the coord so we are in top-bot for PIL coords
			return transpose_y
	
	def move_cube(self, gripper, op, val):
		if gripper is not None:
			if op == 'grip':
				self.mycube.grip(gripper, val)
			elif op == 'twist':
				self.mycube.twist(gripper, val)
		else:
			return self.mycube.move_face_for_twist(val)

if __name__ == '__main__':
	RubikSolverApp().run()
