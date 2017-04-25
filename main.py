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

THRESHOLD = 8 # used to determine how close a color is

# hard-coded instructions for optimizing face scanning
SCANCUBE = [
	('F', 'A'), # U is up
	('U', 'B'), # D is up
	('L', 'B'), # R is up
	('R', 'B'), # L is up
	('L', 'A'), # B is up
	('B', 'B') # F is up
]

COLORS = {
	'red': [1.0, 0.0, 0.0],
	'orange': [1.0, 0.5, 0.0],
	'yellow': [1.0, 1.0, 0.0],
	'green': [0.0, 0.4, 0.0],
	'blue': [0.0, 0.0, 1.0],
	'white': [1.0, 1.0, 1.0],
}

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

class Settings(Screen):
	__sites = {}

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

		for i in rscube.ROT_TABLE[app.mycube.get_up_rot()]:
			site_name = 'center' + str(i)

			box = None
			if site_name in self.__sites:
				box = self.__sites[site_name]
			else:
				box = SiteBox(id=site_name)
				self.__sites[site_name] = box
				self.ids.sites_rel.add_widget(box)

			pos = app.center_to_ll((app.site_center_x[i-1], app.site_center_y[i-1]), (app.crop_size, app.crop_size), app.site_size, True)
			box.size = (self.ids.site_slider.value, self.ids.site_slider.value)
			box.pos = pos

class ColorBox(Label):
	def on_touch_down(self, touch):
		if self.collide_point(*touch.pos):
			if self.id in COLORS:
				App.get_running_app().sm.get_screen('scan').color_touched(self)
			else:
				App.get_running_app().sm.get_screen('scan').site_touched(self)
			return True
	
class Scan(Screen):
	__sites = {}
	__fix_color = None
	
	def on_pre_enter(self):
		x = 30
		y = 235
		for name, color in COLORS.items():
			label = ColorBox(id=name)
			self.ids.scan_float.add_widget(label)
			with label.canvas:
				r, g, b = color
				Color(r, g, b)
				Rectangle(size=(30, 30), pos=(x + 2, y + 2))
			label.pos = (x, y)
			y -= 40

	def on_enter(self):
		# close grippers
		App.get_running_app().mycube.grip('A', 'c')
		App.get_running_app().mycube.grip('B', 'c')
		
		self.scan_index = 0 # reset scan index
		self.scan_cube() # begin scanning cube

	def site_touched(self, site):
		if self.__fix_color is not None:
			fix_color = COLORS[self.__fix_color.id]
			# update the site box with new color
			with site.canvas:
				Color(0, 0, 0)
				Rectangle(size=site.size, pos=site.pos)
				r, g, b = fix_color
				Color(r, g, b)
				Rectangle(size=(site.size[0] - 4, site.size[1] - 4), pos=(site.pos[0] + 2, site.pos[1] + 2))
			
			app = App.get_running_app()
			sitenum = site.id[-1] # site number of corrected site
			
			raw_color = app.colors[self.__fix_color.id] # get raw color corresponding to new color
			app.mycube.set_up_raw_color(sitenum, raw_color) # set raw_color for this site on cube object
	
	def color_touched(self, color):
		if self.__fix_color is not None:
			prev_fix = self.__fix_color
			prev_color = COLORS[self.__fix_color.id]
			with prev_fix.canvas:
				Color(0, 0, 0)
				Rectangle(size=prev_fix.size, pos=(prev_fix.pos))
				r, g, b = prev_color
				Color(r, g, b)
				Rectangle(size=(30, 30), pos=(prev_fix.pos[0] + 2, prev_fix.pos[1] + 2))
		self.__fix_color = color
		fix_color = COLORS[color.id]
		with color.canvas:
			Color(0, 1, 0)
			Rectangle(size=color.size, pos=(color.pos))
			r, g, b = fix_color
			Color(r, g, b)
			Rectangle(size=(30, 30), pos=(color.pos[0] + 2, color.pos[1] + 2))

	def scan_cube(self):
		app = App.get_running_app()
		cube = app.mycube

		for index, tup in enumerate(SCANCUBE):
			if self.scan_index > index: # skip loop until match where scanning left off
				print 'skipping index %i' % index
				continue

			print 'start scanning', index
			print 'cube orientation: %s' % cube.orientation

			# SCANCUBE contains instructions for moving face to to_gripper, specifically for initial cube scan
			face = tup[0]
			to_gripper = tup[1]

			print 'preparing to move face %s to %s' % (face, to_gripper)
			cube.move_face_for_twist(face, to_gripper) # move face to prep for scan
			up_face = cube.orientation[0]
			rot = cube.get_up_rot() # get current rotation of up face
			print 'new cube orientation: %s' % cube.orientation

			# get and update image
			pimg = PILImage.open(rscube.testimages[rscube.FACES[up_face]])
			cimg = crop_pil_img(pimg, app.crop_center, app.crop_size)
			cimg.save('tmp.jpg')

			img = self.ids.scan_img
			img.source = 'tmp.jpg'
			img.size = (app.crop_size, app.crop_size)
			img.reload()

			# scan face
			face_colors = cube.scan_face() # scans face in up position and receives list of colors in sites 1-9 wrt current orientation of cube

			has_unsure_sites = False # flag to identify when a site isn't matched very well
			
			for sitenum in xrange(1, 10): # for each site 1 thru 9
				#print 'starting %i' % sitenum
				site_name = 'center' + str(sitenum)
				pos = app.center_to_ll((app.site_center_x[sitenum - 1], app.site_center_y[sitenum - 1]), (app.crop_size, app.crop_size), app.site_size, True) # get position of this site

				color = face_colors[sitenum - 1] # color in this site

				# get site box for this sitenum
				site = None
				if site_name in self.__sites:
					site = self.__sites[site_name]
				else:
					site = ColorBox(id=site_name)
					self.__sites[site_name] = site
					self.ids.scan_rel.add_widget(site)
					
				site.pos = pos # set site position

				# check against each config face color to find a match
				match_color, last_delta_e = find_closest_color(color, app.colors)
				#print match_color, last_delta_e

				outline_color = (0, 0, 0) # start with a black outline
				# If delta_e is not very low, must not be good match. Flag this face for manual correction
				if last_delta_e > THRESHOLD:
					has_unsure_sites = True
					self.scan_index = index
					outline_color = (1.0, 0.5, 1.0) # give it a pink outline if unsure

				# draw box with matched color
				with site.canvas:
					r, g, b = outline_color
					Color(r, g, b)
					Rectangle(size=site.size, pos=pos)
					r, g, b = COLORS[match_color]
					Color(r, g, b)
					Rectangle(size=(app.site_size - 2, app.site_size - 2), pos=(site.pos[0] + 2, site.pos[1] + 2))
				
			if has_unsure_sites: # break out of for loop if a site was not matched very well
				break
			print 'finished scanning', index
		
		# If we get this far, all sides have been processed and there are no unsure sites.
		# Now cube can set its own face_colors and cube_colors
		#cube.set_face_colors()
		#cube.set_cube_colors()
		self.ids.scan_status.text = ''
		print '*****Done scanning!*****'

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
			color = [float(values[0]), float(values[1]), float(values[2])]
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

def find_closest_color(color, colors_to_check):
	# create Color object from site color and convert to lab color for comparison
	r, g, b = (x / 255.0 for x in color)
	site_color_lab = convert_color(sRGBColor(r, g, b), LabColor)
	last_delta_e = 999
	match_color = None
	for c, val in colors_to_check.items():
		r, g, b = (x / 255.0 for x in val)
		check_color_lab = convert_color(sRGBColor(r, g, b), LabColor) # convert to lab color for comparison
		delta_e = delta_e_cie2000(site_color_lab, check_color_lab)
		if delta_e < last_delta_e: # use this check to find the closest match
			match_color = c
			last_delta_e = delta_e
	return match_color, last_delta_e

if __name__ == '__main__':
	RubikSolverApp().run()
