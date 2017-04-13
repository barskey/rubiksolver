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
from kivy.properties import ObjectProperty

import ConfigParser
from PIL import Image as PILImage

Config.set('graphics', 'width', '480')
Config.set('graphics', 'height', '320')

CONFIGFILE = 'calibrate.txt'
config = ConfigParser.ConfigParser()

SCREEN_SIZE_X = 480 # hard coded for convenience
SCREEN_SIZE_Y = 320 # hard coded for convenience
IMG_SIZE_X = 320 # size of image in x to capture from camera
IMG_SIZE_Y = 240 # side of image in y to capture from camera

class RubikSolver(BoxLayout):
	pass

class MainMenu(Screen):
	pass

class Settings(Screen):
	
	def add_crop_img(self):
		# TODO change this to get actual image from camera
		kim = KvImage(size=(IMG_SIZE_X, IMG_SIZE_Y), source='testimg\\uface.jpg')
		
		self.ids.crop_float.add_widget(kim, 1)
		
	def add_sites_img(self):
		# TODO change this to get actual image from camera
		# load/grab image
		pim = PILImage.open('testimg\\uface.jpg')
		
		# crop image and save to temp file (0,0 is in upper-left)
		size = App.get_running_app().crop_config['size']
		center_x = App.get_running_app().crop_config['center_x']
		center_y = App.get_running_app().crop_config['center_y']
		l = center_x - size / 2
		t = center_y - size / 2
		r = l + size
		b = t + size
		tmp_img = pim.crop((l, t, r, b))
		
		tmp_img.save('tmp.jpg', "JPEG") # TODO should this extension be hard coded?
		
		kim = KvImage(size=(size, size), source='tmp.jpg')
		
		self.ids.sites_float.add_widget(kim)

class DragBox(DragBehavior, Label):
	pass

class RubikSolverApp(App):

	grip_a_config = {}
	grip_b_config = {}
	twist_a_config = {}
	twist_b_config = {}
	crop_config = {}
	site_config = {}

	def build(self):
		self.get_config()
		
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
	transposes local coord from center to ll corner, then transposes to screen coords
	0,0 in ll of screen
	"""
	def get_global_pos(self, coord, dir, size):
		if dir == 'x':
			ll_x = coord - size / 2
			return (ll_x + ((SCREEN_SIZE_X - size) / 2))
		elif dir == 'y':
			ll_y = coord - size / 2
			return (ll_y + ((SCREEN_SIZE_Y - size) / 2))
	
	"""
	transposes global coord from ll corner to center, then transposes to local coords
	0,0 in ll of screen
	"""
	def get_local_pos(self, coord, dir, size):
		if dir == 'x':
			center_x = coord + size / 2
			return (center_x - ((SCREEN_SIZE_X - size) / 2))
		elif dir == 'y':
			center_y = coord + size / 2
			return (center_y - ((SCREEN_SIZE_Y - size) / 2))
	
if __name__ == '__main__':
	RubikSolverApp().run()
