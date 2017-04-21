from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.graphics import *
from kivy.properties import ListProperty, NumericProperty
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
		center = app.ll_to_center((self.x, self.y), (app.crop_size, app.crop_size), app.site_size, True)
		app.update_config('Sites', self.id + '_x', center[0])
		app.update_config('Sites', self.id + '_y', center[1])
		print self.id

class Site(Label):
	pass

class Settings(Screen):
	crop = {}
	sites = {}

	def add_crop_img(self):

		# TODO change this to get actual image from camera
		img = self.ids.crop_img
		img.source = 'testimg/uface.jpg'

	def add_sites_img(self):

		app = App.get_running_app()
		center = (app.crop_center[0], app.crop_center[1])

		# TODO change this to get actual image from camera
		# load/grab image
		pimg = PILImage.open('testimg/uface.jpg')
		cimg = crop_pil_img(pimg, center, app.crop_size)
		cimg.save('tmp.jpg')

		img = self.ids.sites_img
		img.source = 'tmp.jpg'
		img.size = (app.crop_size, app.crop_size)
		img.reload()

		self.add_sites_boxes()

	def add_sites_boxes(self):

		app = App.get_running_app()

		for i in rscube.ROT_TABLE[rscube.UP_FACE_ROT[app.mycube.orientation]]:
			site_name = 'center' + str(i)

			box = None
			if site_name in self.sites:
				box = self.sites[site_name]
			else:
				box = SiteBox(id=site_name)
				self.sites[site_name] = box
				self.ids.sites_rel.add_widget(box)

			pos = app.center_to_ll((app.site_center_x[i-1], app.site_center_y[i-1]), (app.crop_size, app.crop_size), app.site_size, True)
			box.size = (self.ids.site_slider.value, self.ids.site_slider.value)
			box.pos = pos

class Scan(Screen):
	sites = {}

	def on_enter(self):
		self.scan_index = 0
		self.scan_cube()

	def scan_cube(self):

		app = App.get_running_app()
		cube = app.mycube

		for index, tup in enumerate(SCANCUBE):
			if self.scan_index > index: # skip loop until match where scanning left off
				continue

			print 'start scanning', index

			face = tup[0]
			to_gripper = tup[1]

			cube.move_face_for_twist(face, to_gripper) # move face to prep for scan
			up_face = cube.orientation[0]
			rot = rscube.UP_FACE_ROT[cube.orientation] # get current rotation of up face
			print 'up_face:', up_face, 'rot:', rot

			# get and update image
			pimg = PILImage.open(rscube.testimages[rscube.FACES[up_face]])
			cimg = crop_pil_img(pimg, app.crop_center, app.crop_size)
			cimg.save('tmp.jpg')

			img = self.ids.scan_img
			img.source = 'tmp.jpg'
			img.size = (app.crop_size, app.crop_size)
			img.reload()

			# scan face
			face_colors = cube.scan_face() # scans face in up position
			print 'face_colors:', face_colors

			is_missing_color = False
			for i in xrange(1, 10):
				site_name = 'center' + str(i)
				pos = app.center_to_ll((app.site_center_x[i - 1], app.site_center_y[i - 1]), (app.crop_size, app.crop_size), app.site_size, True)
				
				sites_rot = rscube.ROT_TABLE[rot] # for getting site color with cube in rotated position
				rot_index = sites_rot[i - 1]
				color = face_colors[rot_index - 1]
				print 'color:', color, 'rot_index:', rot_index
				
				site = None
				if site_name in self.sites:
					site = self.sites[site_name]
				else:
					site = Site(id=site_name)
					self.sites[site_name] = site
					self.ids.scan_rel.add_widget(site)
				site.pos = pos

				if color is None:
					# add a black box with pink outline
					with site.canvas:
						Color(1, 0.5, 1)
						Rectangle(size=(app.site_size, app.site_size), pos=pos)
						Color(0, 0, 0)
						Rectangle(size=(app.site_size - 2, app.site_size - 2), pos=(pos[0] + 1, pos[1] + 1))
					self.scan_index = index
					is_missing_color = True # break out of for loop at first missing color
					break
				else:
					r, g, b = (x / 255.0 for x in color)
					with site.canvas:
						Color(0, 0, 0)
						Rectangle(size=(app.site_size, app.site_size), pos=pos)
						Color(r, g, b)
						Rectangle(size=(app.site_size - 2, app.site_size - 2), pos=(pos[0] + 1, pos[1] + 1))

			if is_missing_color: # break out of for loop if there was a missing color
				break
			print 'finished scanning', index

class RubikSolverApp(App):

	mycube = None
	grip_a_config = {}
	grip_b_config = {}
	twist_a_config = {}
	twist_b_config = {}
	colors = {}
	crop_size = NumericProperty()
	crop_center = ListProperty([None for i in xrange(3)])
	site_size = NumericProperty()
	site_center_x = ListProperty([None for i in xrange(9)])
	site_center_y = ListProperty([None for i in xrange(9)])

	def build(self):
		self.get_config()

		self.mycube = rscube.MyCube(self.site_center_x, self.site_center_y, self.site_size, self.crop_center, self.crop_size, self.grip_a_config, self.twist_a_config, self.grip_b_config, self.twist_b_config)

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

		self.crop_size = config.getint('Crop', 'size')
		self.crop_center = [config.getint('Crop', 'center_x'), config.getint('Crop', 'center_y')]
		crop_list = self.crop_center, self.crop_size

		if self.mycube:
			self.mycube.crop_rect = crop_list # update cube instance with new values

		for option in config.options('GripA'):
			self.grip_a_config[option] = config.getint('GripA', option)

		for option in config.options('GripB'):
			self.grip_b_config[option] = config.getint('GripB', option)

		for option in config.options('TwistA'):
			self.twist_a_config[option] = config.getint('TwistA', option)

		for option in config.options('TwistB'):
			self.twist_b_config[option] = config.getint('TwistB', option)

		self.site_size = config.getint('Sites', 'size')

		site_list = [None for i in xrange(10)]
		site_list[0] = self.site_size
		for i in xrange(9):
			self.site_center_x[i] = config.getint('Sites', 'center' + str(i+1) + '_x')
			self.site_center_y[i] = config.getint('Sites', 'center' + str(i+1) + '_y')
			site_list[i+1] = (self.site_center_x[i], self.site_center_y[i])
		if self.mycube:
			self.mycube.site_rects = site_list

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
