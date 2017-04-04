from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
#from kivy.uix.boxlayout import BoxLayout
#from kivy.uix.button import Button
#from kivy.uix.image import Image
#from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, NoTransition

Config.set('graphics', 'width', '480')
Config.set('graphics', 'height', '320')

class MainMenu(Screen):
	pass

class Settings(Screen):
	pass

rs = Builder.load_file('rubiksolver.kv')

sm = ScreenManager()
sm.add_widget(MainMenu(name='home'))
sm.add_widget(Settings(name='settings'))

rs.add_widget(sm)

class RubikSolverApp(App):

	def build(self):
		return rs

	def go_screen(self, screen, dir):
		if dir == 'None':
			sm.transition = NoTransition()
		else:
			sm.transition = SlideTransition()
			sm.transition.direction = dir
		sm.current = screen

if __name__ == '__main__':
	RubikSolverApp().run()
