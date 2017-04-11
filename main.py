from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.slider import Slider
from kivy.uix.button import Button
#from kivy.uix.image import Image
#from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition

import ConfigParser

Config.set('graphics', 'width', '480')
Config.set('graphics', 'height', '320')

CONFIGFILE = 'calibrate.txt'
config = ConfigParser.ConfigParser()

class SettingsSlider(Slider):
	pass

class RubikSolver(BoxLayout):
	pass

class MainMenu(Screen):
	pass

class Settings(Screen):
	pass

class RubikSolverApp(App):
	gripper_a = {}
	gripper_b = {}

	def build(self):
		self.get_settings()

		self.sm = ScreenManager()
		self.sm.add_widget(MainMenu(name='home'))
		self.sm.add_widget(Settings(name='settings'))

		rs = RubikSolver()
		rs.add_widget(self.sm)

		return rs

	def go_screen(self, screen, dir):
		if dir == 'None':
			self.sm.transition = NoTransition()
		else:
			self.sm.transition = SlideTransition()
			self.sm.transition.direction = dir
		self.sm.current = screen

	def get_settings(self):
		config.read(CONFIGFILE)
		for option in config.options('GripperA'):
			self.gripper_a[option] = config.getint('GripperA', option)

		for option in config.options('GripperB'):
			self.gripper_b[option] = config.getint('GripperB', option)

	def update_settings(self, setting, option, value):
		# TODO move gripper

		config.set(setting, option, str(int(value)))
		with open(CONFIGFILE, 'wb') as configfile:
			config.write(configfile)
		self.get_settings()

if __name__ == '__main__':
	RubikSolverApp().run()
