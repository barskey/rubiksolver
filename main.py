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
from PIL import Image as PILImage
import ConfigParser
import time

import rscube

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
	crop = {}
	sites = {}

	def add_crop_img(self):

		# TODO change this to get actual image from camera
		img = self.ids.crop_img
		img.source = 'testimg\\uface.jpg'

	def add_sites_img(self):
	
		app = App.get_running_app()
		crop_config = app.crop_config
		center = (crop_config['center_x'], crop_config['center_y'])
		size = crop_config['size']

		# TODO change this to get actual image from camera
		# load/grab image
		pimg = PILImage.open('testimg\\uface.jpg')
		cimg = crop_pil_img(pimg, center, size)
		cimg.save('tmp.jpg')
		
		img = self.ids.sites_img
		img.source = 'tmp.jpg'
		img.size = (size, size)
		img.reload()
		
		self.add_sites_boxes()

	def add_sites_boxes(self):
	
		app = App.get_running_app()
		site_config = app.site_config
		size = site_config['size']

		for i in rscube.ROT_TABLE[cube.orientation]:
			site_name = 'center' + str(i)
			
			box = None
			if site_name in self.sites:
				box = self.sites[site_name]
			else:
				box = SiteBox(id=site_name)
				self.sites[site_name] = box
				self.ids.sites_rel.add_widget(box)

			pos = app.center_to_ll((site_config[site_name]['x'], site_config[site_name]['y']), (app.crop_config['size'], app.crop_config['size']), size, True)
			box.size = (self.ids.site_slider.value, self.ids.site_slider.value)
			box.pos = pos
			
class Scan(Screen):
	sites = {}
		
	def on_enter(self):
		self.scan_cube()
	
	def scan_cube(self):
		app = App.get_running_app()
		site_config = app.site_config
		size = site_config['size']
		cube = app.mycube
		
		crop_config = app.crop_config
		crop_center = (crop_config['center_x'], crop_config['center_y'])
		crop_size = crop_config['size']

		for tup in SCANCUBE:
			face = tup[0]
			to_gripper = tup[1]
			cube.move_face_for_twist(face, to_gripper) # move face to prep for scan
			up_face = cube.orientation[0]
			
			# get and update image
			pimg = PILImage.open(rscube.testimages[rscube.FACES[up_face]])
			cimg = crop_pil_img(pimg, crop_center, crop_size)
			cimg.save('tmp.jpg')
			
			img = self.ids.scan_img
			img.source = 'tmp.jpg'
			img.size = (size, size)
			img.reload()
					
			# scan face
			face_colors = cube.scan_face() # scans face in up position
			i = 1
			for color in face_colors:
				site_name = 'center' + str(i)
				pos = app.center_to_ll((site_config[site_name]['x'], site_config[site_name]['y']), (app.crop_config['size'], app.crop_config['size']), size, True)
				
				site = None
				if site_name in self.sites:
					site = self.sites[site_name]
				else:
					site = Site(id=str(i))
					self.sites[site_name] = site
					self.ids.scan_rel.add_widget(site)

				if color is None:
					with site.canvas:
						Color(1, 0.5, 1)
						Rectangle(size=(size, size), pos=pos)
						Color(0, 0, 0)
						Rectangle(size=(size - 2, size - 2), pos=(pos[0] + 1, pos[1] + 1))
				else:
					r, g, b = (x / 255.0 for x in color)
					with site.canvas:
						Color(0, 0, 0)
						Rectangle(size=(size, size), pos=pos)
						Color(r, g, b)
						Rectangle(size=(size - 2, size - 2), pos=(pos[0] + 1, pos[1] + 1))

				site.pos = pos
				#time.sleep(5)
					
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
	
	def move_cube(self, gripper, op, val):
		if gripper is not None:
			if op == 'grip':
				self.mycube.grip(gripper, val)
			elif op == 'twist':
				self.mycube.twist(gripper, val)
		else:
			return self.mycube.move_face_for_twist(val)

def crop_pil_img(img, center, size):
	l = center[0] - size / 2
	r = l + size
	t = center[1] - size / 2
	b = t + size
	return img.crop((l, t, r, b))

			
if __name__ == '__main__':
	RubikSolverApp().run()
