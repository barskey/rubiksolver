from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.core.window import Window
from kivy.graphics import *
from kivy.properties import ListProperty, NumericProperty
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.label import Label
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image as KvImage
from kivy.uix.behaviors import DragBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition
from kivy.uix.bubble import Bubble, BubbleButton

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
from PIL import Image as PILImage
import ConfigParser
import time
from functools import partial

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
	('D', 'B'), # U is up
	('U', 'B'), # D is up
	('L', 'B'), # R is up
	('R', 'B'), # L is up
	('F', 'B'), # B is up
	('B', 'B')  # F is up
]

COLORS = {
	'red': [1.0, 0.0, 0.0],
	'orange': [1.0, 0.5, 0.0],
	'yellow': [1.0, 1.0, 0.0],
	'green': [0.0, 0.4, 0.0],
	'blue': [0.0, 0.0, 1.0],
	'white': [1.0, 1.0, 1.0],
}

# used for retrieving COLORS in pretty rainbow order
CKEYS = [
	'red',
	'orange',
	'yellow',
	'green',
	'blue',
	'white'
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

	def on_touch_down(self, touch):
		app = App.get_running_app()

		if self.collide_point(*touch.pos):
			app.sm.get_screen('settings').set_touched_color(self)

		return super(SiteBox, self).on_touch_down(touch)

class LabelBox(Label):
	def on_touch_down(self, touch):
		app = App.get_running_app()
		
		if self.collide_point(*touch.pos):
			app.sm.get_screen('settings').set_selected_color(self)
			return True

class Settings(Screen):
	_sites_boxes = {}
	_colors_boxes = {}
	_selected_color = None

	def add_img(self, img, crop=True):
		app = App.get_running_app()
		center = (app.crop_center[0], app.crop_center[1])

		# TODO change this to get actual image from camera
		# load/grab image
		if crop is True:
			pimg = PILImage.open('testimg/uface.jpg')
			cimg = crop_pil_img(pimg, center, app.crop_size)
			cimg.save('tmp.jpg')

			img.source = 'tmp.jpg'
			img.size = (app.crop_size, app.crop_size)
			img.reload()
		else:
			img.source = 'testimg/uface.jpg'

	def add_boxes(self, rl):
		app = App.get_running_app()

		for i in range(1, 10):
			site_name = 'center' + str(i)

			box = None
			if site_name in self._sites_boxes:
				box = self._sites_boxes[site_name]
			else:
				box = SiteBox(id=site_name)
				self._sites_boxes[site_name] = box
				rl.add_widget(box)

			pos = app.center_to_ll((app.site_center_x[i-1], app.site_center_y[i-1]), (app.crop_size, app.crop_size), app.site_size, True)
			box.size = (app.site_size, app.site_size)
			box.pos = pos
	
	def add_colors(self, rl):
		x = 240
		y = 170
		
		for color in CKEYS:
			label = LabelBox(id=color)
			rl.add_widget(label)
			raw_rgb = App.get_running_app().colors[color]
			with label.canvas:
				r, g, b = COLORS[color]
				Color(r, g, b)
				Rectangle(size=(32, 32), pos=(x + 2, y + 2))
				r2, g2, b2 = raw_rgb
				Color(r2/255, g2/255, b2/255)
				Rectangle(size=(32, 32), pos=(x + 34, y + 2))
			label.pos = (x, y)
			y -= 40
			
	def set_selected_color(self, site):
		if self._selected_color is not None:
			col = ','.join(format(x, '1.0f') for x in self._selected_color)
			App.get_running_app().update_config('Colors', site.id, col)
			with site.canvas:
				r, g, b = self._selected_color
				Color(r/255, g/255, b/255)
				Rectangle(size=(32, 32), pos=(site.x + 34, site.y + 2))
			self._selected_color = None

	def set_touched_color(self, site):
		face_colors = App.get_running_app().mycube.scan_face()
		sitenum = int(site.id[-1]) - 1
		self._selected_color = face_colors[sitenum]

class ColorBox(Label):
	def on_touch_down(self, touch):
		if self.collide_point(*touch.pos):
			App.get_running_app().sm.get_screen('scan').site_touched(self, self.pos)
			return True

class SelectDropdown(DropDown):
	def on_select(self, data):
		app = App.get_running_app()
		scr = app.sm.get_screen('solve')
		btn = scr.ids.btn_select
		img = scr.ids.img_solve
		
		btn.text = data
		scr.ids.solve_to.text = data
		app.mycube.solve_to = data
		if app.mycube.set_solve_string() >= 0: # TODO verify what the solve method actually returns
			moves = str(len(app.mycube.get_solve_string().split(' ')))
			scr.ids.moves_req.text = moves # TODO add case for non int moves
			
		newsrc = None # TODO set image to question mark img in case can't find solve to img
		newsrc = 'data/' + rscube.PATTERNS[data][0]
		img.source = newsrc

class SolveLabel(Label):
	pass
	
class Solve(Screen):
	def on_pre_enter(self):
		img = self.ids.img_solve
		img.source = 'data/_solid.jpg'
	
		self._dropdown = SelectDropdown()
		# add each solve to pattern to dropdown
		for solution in sorted(rscube.PATTERNS):
			btn = Button(text=solution, size_hint_y=None, height=40)
			btn.bind(on_release=lambda btn: self._dropdown.select(btn.text))
			self._dropdown.add_widget(btn)
		
		cube = App.get_running_app().mycube
		self.ids.solve_to.text = 'Solid Cube'
		self.ids.moves_req.text = str(len(cube.get_solve_string().split(' ')))
	
	def run_solve(self):
		app = App.get_running_app()
		cube  = app.mycube
		solve_string = cube.get_solve_string()
		if solve_string:
			print 'Solving...'
			self.ids.btn_solve.text = 'Solving...'
			self.ids.btn_solve.disabled = True
			self.ids.btn_select.disabled = True
			count = len(solve_string.split(' '))
			for move in solve_string.split(' '):
				print 'move', move
				face = move[0] # first char is which face to move
				dir = move[1] if len(move) > 1 else '+' # second char will be either ` or 2. 
				gripper = cube.move_face_for_twist(face) # returns gripper to which face was moved
				if dir == "'": # CCW
					cube.twist(gripper, '-') # twist CCW
					cube.grip(gripper, 'o') # open gripper
					cube.twist(gripper, '+') # twist back to start
					cube.grip(gripper, 'c') # close gripper
				elif dir == '2': # twist twice
					cube.twist(gripper, '+')
					cube.twist(gripper, '+')
				else: # CW
					cube.twist(gripper, dir) # twist CW
					cube.grip(gripper, 'o') # open gripper
					cube.twist(gripper, '-') # twist back to start
					cube.grip(gripper, 'c') # close gripper
				count = count - 1
				self.ids.moves_req.text = str(count)
			print '-------------'
			print 'Done Solving!'
			# set all the cube sites based on the solve to string
			counter = 0
			st = cube.solve_to
			for f in range(6):
				for s in range(9):
					mc = cube._face_colors[rscube.FACES[st[counter]]]
					cube._match_colors[f][s] = mc
					cube._raw_colors[f][s] = app.colors[mc]
					counter = counter + 1
			cube.set_face_colors()
			cube.set_cube_colors()
			self.ids.btn_solve.text = 'Solve'
			self.ids.btn_solve.disabled = False
			self.ids.btn_select.disabled = False

class ColorBubble(Bubble):
	pass

class CBButton(BubbleButton):
	def on_release(self):
		app = App.get_running_app()
		scr = app.sm.get_screen('scan')
		site = scr._site_touched
		fix_color = COLORS[self.id]
		# update the site box with new color
		with site.canvas:
			Color(0, 0, 0)
			Rectangle(size=site.size, pos=site.pos)
			r, g, b = fix_color
			Color(r, g, b)
			Rectangle(size=(site.size[0] - 4, site.size[1] - 4), pos=(site.pos[0] + 2, site.pos[1] + 2))

		# remove the Bubble widget
		bubble = scr._bubble
		scr.remove_widget(bubble)
		scr._bubble = None

		cube = app.mycube
		sitenum = site.id[-1] # site number of corrected site

		raw_color = app.colors[self.id] # get raw color corresponding to new color
		cube.set_up_raw_color(sitenum, raw_color) # set raw_color for this site on cube object
		cube.set_up_match_color(int(sitenum), self.id) # set match_color for this site on cube object
		print 'Set site %s match_color to %s.' % (sitenum, self.id)
		
		# enable the button if all the sites on this face have been matched
		if cube.check_face_matched(cube.get_up_face()[0]):
			scr.ids.btn_next.disabled = False
	
class Scan(Screen):
	_sites = {}
	_bubble = None
	_site_touched = None

	def on_enter(self):
		# close grippers
		App.get_running_app().mycube.grip('A', 'c')
		App.get_running_app().mycube.grip('B', 'c')

		self._index = 0 # for SCANCUBE list
		self.scan_cube() # begin scanning cube

	def site_touched(self, site, pos):
		if self._bubble is not None: # check if widget has been already added
			self.remove_widget(self._bubble) # remove existing bubble
			self._bubble = None # set 'pointers' to none
			self._site_touched = None # set 'pointers' to none
		else:
			self._bubble = bubble = ColorBubble() # create a new bubble object
			bubble.size_hint = (None, None)
			bubble.size = (240, 45)
			for color in CKEYS: # set the colors of the buttons
				cb = CBButton()
				cb.id = color
				rgb = [a for a in COLORS[color]]
				rgb.append(1)
				cb.background_color = rgb
				cb.background_normal = ''
				bubble.add_widget(cb)

			bubble.arrow_pos = 'top_mid'
			bubble.pos = (pos[0] + 45, pos[1] + 20) # position figured out by trial and error
			self.add_widget(bubble) # add bubble widget to screen widget (scan)
			self._site_touched = site # set 'pointer' for site touched

	def scan_cube(self):
		"""
		Calls scan_face for each face. Gets called when scan is good or button is touched.
		"""
		app = App.get_running_app()
		cube = app.mycube

		self.ids.btn_next.text = 'Next'

		if self._index < 6:
			good_scan = self.scan_face(self._index)
			if good_scan:
				# increment the index for the next face and scan next face
				self._index = self._index + 1
				self.scan_cube()
			else:
				self.ids.scan_status.text = 'Touch the boxes shown in pink\nto fix the colors.'
				self.ids.scan_status.color = (1, 0, 0, 1)
				self.ids.btn_next.disabled = True
				self._index = self._index + 1 # increment the index for the next face when button is enabled
		else:
			# move U back to top
			print 'Move face U back to top'
			print 'Moving face %s to %s.' % ('F', 'A')
			cube.move_face_for_twist('F', 'A') # move face to get back to original position
			print 'Moving face %s to %s.' % ('D', 'B')
			cube.move_face_for_twist('D', 'B') # move face to get back to original position
			print cube.orientation # debug
			
			# If we get this far, all sides have been processed and face colors have been set.
			# Check that there are exactly 9 of each color
			if cube.check_all_sites():
				cube.set_face_colors() # cube can set its own face_colors
			else:
				self.ids.scan_status.text = "I didn't count exactly 9 of each color.\nLet's try scanning again."
				self.ids.scan_status.color = (1, 0, 0, 1)
				self.ids.btn_next.text = 'Re-Scan'
				print 'check_all_sites returned False'
				cube.clear_matched() # clear the matched colors so we can start over
				self._index = 0
				return
				
			# Now check that all faces have a unique color before setting cube colors.
			if cube.check_face_colors():
				cube.set_cube_colors() # Now cube can set its own cube_colors
			else:
				self.ids.scan_status.text = "Center colors aren't correct.\nLet's try scanning again."
				self.ids.scan_status.color = (1, 0, 0, 1)
				self.ids.btn_next.text = 'Re-Scan'
				print 'Check_face_colors returned False'
				cube.clear_matched() # clear the matched colors so we can start over
				self._index = 0
				return

			# Now check that cube can generate a solve string.
			if cube.set_solve_string() < 0: # returns error code if solve string is not valid
				self.ids.scan_status.text = "Oops. I don't think I got that scan right.\nLet's re-scan and check every color."
				self.ids.scan_status.color = (1, 0, 0, 1)
				self.ids.btn_next.text = 'Re-Scan'
				print 'set_solve_string returned non-zero'
				cube.clear_matched() # clear the matched colors so we can start over
				self._index = 0
			else:
				#cube.set_cube_colors()
				print '*****Done scanning!*****'
				self.ids.scan_status.text = 'Scanning complete!'
				self.ids.scan_status.color = (0, 1, 0, 1)
				self.ids.btn_next.text = 'Done'
				app.go_screen('solve', 'left')
	
	def scan_face(self, index):
		"""
		Moves face according to instructions in SCANCUBE, then scans face.
		Returns False if any unsure sites, otherwise True.
		"""
		app = App.get_running_app()
		cube = app.mycube

		print '-------------------------'
		print 'Begin scanning %i.' % index
		print 'Cube orientation: %s' % cube.orientation

		# SCANCUBE contains instructions for moving face to to_gripper, specifically for initial cube scan
		face, to_gripper = SCANCUBE[index]

		# move cube to next face
		print 'Moving face %s to %s.' % (face, to_gripper)
		self.ids.scan_status.text = 'Preparing to scan...'
		cube.move_face_for_twist(face, to_gripper) # move face to prep for scan

		up_face = cube.orientation[0] # get current up face
		rot = cube.get_up_rot() # get current rotation of up face
		self.ids.scan_status.text = 'Scanning face %s...' % up_face

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

		for sitenum in range(1, 10): # for each site 1 thru 9
			#print 'starting %i' % sitenum # debug
			site_name = 'center' + str(sitenum)
			pos = app.center_to_ll((app.site_center_x[sitenum - 1], app.site_center_y[sitenum - 1]), (app.crop_size, app.crop_size), app.site_size, True) # get position of this site

			color = face_colors[sitenum - 1] # color in this site

			# get site box for this sitenum
			site = None
			if site_name in self._sites:
				site = self._sites[site_name]
			else:
				site = ColorBox(id=site_name)
				self._sites[site_name] = site
				self.ids.scan_rel.add_widget(site)

			site.pos = pos # set site position

			# check against each config face color to find a match
			match_color, delta_e = find_closest_color(color, app.colors)
			#print match_color, delta_e # debug

			outline_color = (0, 0, 0) # start with a black outline
			# If delta_e is high, must not be good match. Flag this face for manual correction
			if delta_e > THRESHOLD:
				has_unsure_sites = True
				print '** Unsure site found at %i' % sitenum
				print color
				outline_color = (1.0, 0.5, 1.0) # give it a pink outline if unsure
			else:
				# set match_color to this site on this face
				cube.set_up_match_color(sitenum, match_color)

			# draw box with matched color
			with site.canvas:
				r, g, b = outline_color
				Color(r, g, b)
				Rectangle(size=site.size, pos=pos)
				r, g, b = COLORS[match_color]
				Color(r, g, b)
				Rectangle(size=(site.size[0] - 4, site.size[1] - 4), pos=(site.pos[0] + 2, site.pos[1] + 2))

		if has_unsure_sites: # if one of the 9 sites was not matched very well
			print '** Unsure site(s) when scanning face %s (index %i)' % (up_face, index)
			return False
		else: # face has been scanned and there are no unsure sites
			print '--------------------------------'
			print 'Finished scanning %i. GOOD SCAN.' % index
			return True
	
class RubikSolverApp(App):

	mycube = None
	grip_a_config = {}
	grip_b_config = {}
	twist_a_config = {}
	twist_b_config = {}
	colors = {}
	crop_size = NumericProperty()
	crop_center = ListProperty([None for i in range(3)])
	site_size = NumericProperty()
	site_center_x = ListProperty([None for i in range(9)])
	site_center_y = ListProperty([None for i in range(9)])

	def build(self):
		self.get_config()

		self.mycube = rscube.MyCube(self.site_center_x, self.site_center_y, self.site_size, self.crop_center, self.crop_size, self.grip_a_config, self.twist_a_config, self.grip_b_config, self.twist_b_config)

		self.imgx = IMG_SIZE_X
		self.imgy = IMG_SIZE_Y

		self.sm = ScreenManager()
		self.sm.add_widget(MainMenu(name='home'))
		self.sm.add_widget(Settings(name='settings'))
		self.sm.add_widget(Scan(name='scan'))
		self.sm.add_widget(Solve(name='solve'))

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

		site_list = [None for i in range(10)]
		site_list[0] = self.site_size
		for i in range(9):
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
		val = None
		try:
			val = int(value)
		except ValueError:
			val = value
		config.set(setting, option, str(val))
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
