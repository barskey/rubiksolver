from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.graphics import *
from kivy.properties import StringProperty
#from kivy.uix.button import Button
from kivy.uix.image import Image as KvImage
#from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.behaviors import DragBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

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

# hard-coded instructions for optimizing face scanning
SCANCUBE = [
	('F', 'A'), # U is up
	('U', 'B'), # D is up
	('L', 'B'), # R is up
	('R', 'B'), # L is up
	('L', 'A'), # B is up
	('B', 'B') # F is up
]

class RubikSolver(BoxLayout):
	pass

class MainMenu(Screen):
	pass

class DragBox(DragBehavior, Label):
	pass

class SiteBox(DragBehavior, Label):

	def on_pos(self, *args):
		app = App.get_running_app()
		imgsize = app.crop_config['size']
		size = app.site_config['size']
		center = app.ll_to_center((self.x, self.y), (imgsize, imgsize), size, True)
		app.update_config('Sites', self.id + '_x', center[0])
		app.update_config('Sites', self.id + '_y', center[1])

class Site(Label):
	pass
		
class Settings(Screen):
	kim_crop = None
	kim_sites = None

	def add_crop_img(self):

		# TODO change this to get actual image from camera
		img = self.ids.crop_img
		img.source = 'testimg\\uface.jpg'

	def add_sites_img(self):

		# TODO change this to get actual image from camera
		# load/grab image
		img = self.ids.sites_img
		img.source = 'tmp.jpg'

	def add_sites_boxes(self):
	
		for widget in self.ids:
			print widget
			#if self.ids[widget].id.startswith ('center'):
			#	self.remove_widget(widget)

		app = App.get_running_app()
		site_config = app.site_config
		size = site_config['size']

		for i in xrange(1, 10):
			site_name = 'center' + str(i)
			box = SiteBox(id=site_name)
			self.ids.sites_rel.add_widget(box)

			pos = app.center_to_ll((site_config[site_name]['x'], site_config[site_name]['y']), (app.crop_config['size'], app.crop_config['size']), size, True)

			box.width = site_config['size']
			box.height = site_config['size']
			box.pos = pos

class Scan(Screen):
		
	def on_enter(self):
		#self.scan_cube()
		pass
	
	def scan_cube(self):
		app = App.get_running_app()
		site_config = app.site_config
		size = site_config['size']
		cube = app.mycube

		for tup in SCANCUBE:
			face = tup[0]
			to_gripper = tup[1]
			cube.move_face_for_twist(face, to_gripper)
			face_colors = cube.scan_face()
			i = 1
			for color in face_colors:
				if color is None:
					print 'No color, site: %s' % str(i)
				else:
					site_name = 'center' + str(i)

					x = app.get_screen_pos(site_config[site_name]['x'], 'x', size, app.crop_config['size'])
					y = app.get_screen_pos(site_config[site_name]['y'], 'y', size, app.crop_config['size'])
					
					site = Site(id=str(i))
					self.ids.scan_float.add_widget(site)
					site.width = size
					site.height = size
					site.pos = (x, y)
					
					i += 1
			
class RubikSolverApp(App):

	grip_a_config = {}
	grip_b_config = {}
	twist_a_config = {}
	twist_b_config = {}
	crop_config = {}
	site_config = {}
	colors = {}

	def build(self):
		self.get_config()

		self.mycube = rscube.MyCube(self.site_config, self.crop_config, self.grip_a_config, self.twist_a_config, self.grip_b_config, self.twist_b_config)

		self.imgx = IMG_SIZE_X
		self.imgy = IMG_SIZE_Y

		self.sm = ScreenManager()
		self.sm.add_widget(MainMenu(name='home'))
		self.sm.add_widget(Settings(name='settings'))
		self.sm.add_widget(Scan(name='scan'))

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
		
		for option in config.options('Colors'):
			values = config.get('Colors', option).split(',')
			color = (float(values[0]), float(values[1]), float(values[2]))
			self.colors[option] = color

	def update_config(self, setting, option, value):
		# TODO move gripper

		config.set(setting, option, str(int(value)))
		with open(CONFIGFILE, 'wb') as configfile:
			config.write(configfile)
		self.get_config()

	def center_to_ll(self, center, img_size, size, flipy = False):
		ll_x = center[0] - size / 2
		ll_y = None
		if flipy:
			ll_y = center[1] + size / 2
			ll_y = img_size[1] - ll_y
		else:
			ll_y = center[1] - size / 2
		return (ll_x, ll_y)
	
	def ll_to_center(self, ll, img_size, size, flipy = False):
		center_x = ll[0] + size / 2
		center_y = None
		if flipy:
			center_y = ll[1] + size / 2
			center_y = img_size[1] - center_y
		else:
			center_y = ll[1] - size / 2
		return (center_x, center_y)
	
	def get_screen_pos(self, coord, dir, box_size, img_size):
		'''
		transposes PIL coord from center to ll corner, then to screen coords
		return wrt 0,0 in ll of screen
		'''
		if dir == 'x':
			ll_x = coord - box_size / 2 # move coord to ll corner in x
			offset_x = ll_x + (SCREEN_SIZE_X - img_size) / 2 # add to account for screen space to left of img
			return offset_x
		elif dir == 'y':
			ll_y = coord + box_size / 2 # move coord to ll corner in y
			transpose_y = img_size - ll_y # flip the coord so we are in bot-top for screen coords
			offset_y = transpose_y + (SCREEN_SIZE_Y - TAB_SIZE - img_size) / 2 # add screen space below img
			return offset_y

	def get_PIL_pos(self, coord, dir, box_size, img_size):
		'''
		transposes screen coord from ll corner to center, then to PIL coords
		return wrt 0,0 in ul of screen
		'''
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

def crop_img(PILimg, center, size):
	l = center[0] - size / 2
	t = center[1] - size / 2
	r = l + size
	b = t + size
	return PILimg.crop((l, t, r, b))

			
if __name__ == '__main__':
	RubikSolverApp().run()
