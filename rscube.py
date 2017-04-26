#from kociemba import solve
from PIL import Image, ImageStat
#import RPi.GPIO as GPIO

PINS = {
	'twistA': 1,
	'gripA' : 2,
	'twistB': 3,
	'gripB' : 4
}

# Setup position pin GPIOs as inputs
#GPIO.setmode(GPIO.BCM)
#for pin, gpio_port in PINS.items():
#	GPIO.setup(gpio_port, GPIO.IN)

U = 0
R = 1
F = 2
D = 3
L = 4
B = 5

FACES = {
	'U': U,
	'R': R,
	'F': F,
	'D': D,
	'L': L,
	'B': B
}

FACES_STR = ['U', 'R', 'F', 'D', 'L', 'B']

# ----------------------------------------------------------------------
# Lookup table to store moves to put given face to gripper A or B.
# Relative to cube in default position ordered URFDLB
# e.g. MOVES_TO_A[D] would be the moves to get face currently in position D to gripper A
#
# String is comma separated moves, with the following commands:
# Note: using lower case o and c so it doesn't look like 0
# A : gripper A (front gripper)
# B : gripper B (back gripper)
# o : Open
# c : Close
# + : Clockwise turn
# - : Counter-clockwise turn
MOVES_TO_A = [
	'Bo,A-,Bc,Ao,B+,A+,Ac,Bo,B-,Bc', 'Ao,B-,Ac,Bo,B+,Bc', '', 'Bo,A+,Bc,Ao,B+,A-,Ac,Bo,B-,Bc', 'Ao,B+,Ac,Bo,B-,Bc', 'Ao,B+,B+,Ac'
]

MOVES_TO_B = [
	'Bo,A+,A+,Bc', 'Bo,A+,Bc,Ao,A-,Ac', 'Ao,B+,Ac,Bo,B-,A+,Bc,Ao,A-,Ac', '', 'Bo,A-,Bc,Ao,A+,Ac', 'Ao,B+,Ac,Bo,B-,A-,Bc,Ao,A+,Ac'
]

# Lookup table for new orientation after twisting gripper A or B with the cube in the given position
# e.g. NEW_ORIENTATION_TWISTA['UFD']['+'] gives 'LDR', which the cube will be in after twisting gripper A CW
NEW_ORIENTATION_TWISTA = {
	'UFD': {'+': 'LFR', '-': 'RFL'},
	'URD': {'+': 'FRB', '-': 'BRF'},
	'UBD': {'+': 'RBL', '-': 'LBR'},
	'ULD': {'+': 'BLF', '-': 'FLB'},
	'RDL': {'+': 'FDB', '-': 'BDF'},
	'RBL': {'+': 'DBU', '-': 'UBD'},
	'RUL': {'+': 'BUF', '-': 'FUB'},
	'RFL': {'+': 'UFD', '-': 'DFU'},
	'FDB': {'+': 'LDR', '-': 'RDL'},
	'FRB': {'+': 'DRU', '-': 'URD'},
	'FUB': {'+': 'RUL', '-': 'LUR'},
	'FLB': {'+': 'ULD', '-': 'DLU'},
	'DBU': {'+': 'LBR', '-': 'RBL'},
	'DRU': {'+': 'BRF', '-': 'FRB'},
	'DFU': {'+': 'RFL', '-': 'LFR'},
	'DLU': {'+': 'FLB', '-': 'BLF'},
	'LDR': {'+': 'BDF', '-': 'FDB'},
	'LFR': {'+': 'DFU', '-': 'UFD'},
	'LUR': {'+': 'FUB', '-': 'BUF'},
	'LBR': {'+': 'UBD', '-': 'DBU'},
	'BDF': {'+': 'RDL', '-': 'LDR'},
	'BLF': {'+': 'DLU', '-': 'ULD'},
	'BUF': {'+': 'LUR', '-': 'RUL'},
	'BRF': {'+': 'URD', '-': 'DRU'}
}

NEW_ORIENTATION_TWISTB = {
	'UFD': {'+': 'ULD', '-': 'URD'},
	'URD': {'+': 'UFD', '-': 'UBD'},
	'UBD': {'+': 'URD', '-': 'ULD'},
	'ULD': {'+': 'UBD', '-': 'UFD'},
	'RDL': {'+': 'RFL', '-': 'RBL'},
	'RBL': {'+': 'RDL', '-': 'RUL'},
	'RUL': {'+': 'RBL', '-': 'RFL'},
	'RFL': {'+': 'RUL', '-': 'RDL'},
	'FDB': {'+': 'FLB', '-': 'FRB'},
	'FRB': {'+': 'FDB', '-': 'FUB'},
	'FUB': {'+': 'FRB', '-': 'FLB'},
	'FLB': {'+': 'FUB', '-': 'FDB'},
	'DBU': {'+': 'DLU', '-': 'DRU'},
	'DRU': {'+': 'DBU', '-': 'DFU'},
	'DFU': {'+': 'DRU', '-': 'DLU'},
	'DLU': {'+': 'DFU', '-': 'DBU'},
	'LDR': {'+': 'LBR', '-': 'LFR'},
	'LFR': {'+': 'LDR', '-': 'LUR'},
	'LUR': {'+': 'LFR', '-': 'LBR'},
	'LBR': {'+': 'LUR', '-': 'LDR'},
	'BDF': {'+': 'BRF', '-': 'BLF'},
	'BLF': {'+': 'BDF', '-': 'BUF'},
	'BUF': {'+': 'BLF', '-': 'BRF'},
	'BRF': {'+': 'BUF', '-': 'BDF'}
}
# Translate table to get from current orientation to representation as if in default position
# Order of faces is URFDLB - e.g. for face_position['RUL'], R is in default U, F is in default R, U is in default F, etc.
# so face_position['RUL'][L] gives face B in the default L position
FACE_POSITION = {
	'UFD': [U, R, F, D, L, B],
	'URD': [U, B, R, D, F, L],
	'UBD': [U, L, B, D, R, F],
	'ULD': [U, F, L, D, B, R],
	'RDL': [R, B, D, L, F, U],
	'RBL': [R, U, B, L, D, F],
	'RUL': [R, F, U, L, B, D],
	'RFL': [R, D, F, L, U, B],
	'FDB': [F, R, D, B, L, U],
	'FRB': [F, U, R, B, D, L],
	'FUB': [F, L, U, B, R, D],
	'FLB': [F, D, L, B, U, R],
	'DBU': [D, R, B, U, L, F],
	'DRU': [D, F, R, U, B, L],
	'DFU': [D, L, F, U, R, B],
	'DLU': [],
	'LDR': [L, F, D, R, B, U],
	'LFR': [L, U, F, R, D, B],
	'LUR': [L, B, U, R, F, D],
	'LBR': [L, D, B, R, U, F],
	'BDF': [B, L, D, F, R, U],
	'BLF': [B, U, L, F, D, R],
	'BUF': [B, R, U, F, L, D],
	'BRF': [B, D, R, F, U, L]
}

# Lookup table for current rotation of up face when cube is in designated orientation
# degrees up face is rotated (CW) wrt looking at up face
UP_FACE_ROT = {
	'UFD': 0,
	'URD': 90,
	'UBD': 180,
	'ULD': 270,
	'RDL': 0,
	'RBL': 90,
	'RUL': 180,
	'RFL': 270,
	'FDB': 0,
	'FRB': 90,
	'FUB': 180,
	'FLB': 270,
	'DBU': 0,
	'DRU': 90,
	'DFU': 180,
	'DLU': 270,
	'LDR': 0,
	'LFR': 90,
	'LUR': 180,
	'LBR': 270,
	'BDF': 0,
	'BLF': 90,
	'BUF': 180,
	'BRF': 270
}

# Lookup table to reorder list corresponding to given orientation
# need to subtract 1 from this number to get index
ROT_TABLE = {
	0: [1, 2, 3, 4, 5, 6, 7, 8, 9],
	90: [7, 4, 1, 8, 5, 2, 9, 6, 3],
	180: [9, 8, 7, 6, 5, 4, 3, 2, 1],
	270: [3, 6, 9, 2, 5, 8, 1, 4, 7]
}

testimages = [
	'testimg/uface.jpg',
	'testimg/rface.jpg',
	'testimg/fface.jpg',
	'testimg/dface.jpg',
	'testimg/lface.jpg',
	'testimg/bface.jpg'
]

class MyCube(object):

	def __init__(self, site_center_x, site_center_y, site_size, crop_center, crop_size, grip_a, twist_a, grip_b, twist_b):
		self.__raw_colors = [[None for i in range(9)] for j in range(6)] # luminance for each raw color found on cube
		self.__face_colors = [None for i in range(6)] # color of the center site on each face
		self.__cube_colors = [[None for i in range(9)] for j in self.__face_colors] # corresponding face color for each site on cube
		self.__cube_def = None # string representing cube in order U1U2U3...R1...F1...etc
		self.solve_to = None # string representing cube solve pattern, None to solve to standard
		self.__solve_string = None # instructions to solve cube

		self.__grip_state = {'A': None, 'B': None}

		site_list = [None for i in xrange(10)] # site_rects expects list of 10, 0 is size, 1-9 are (x,y) tuples
		site_list[0] = site_size
		for i in xrange(9):
			site_list[i+1] = (site_center_x[i], site_center_y[i])
		self.site_rects = site_list

		config_list = crop_center, crop_size # crop_rect expects list of 2: [(x,y), size]
		self.crop_rect = config_list

		self.orientation = 'UFD' # current orientation of the cube, Upface, gripper A Face, gripper B Face

		# initialiaze both grippers to load position
		self.grip('A', 'l')
		self.grip('B', 'l')

	@property
	def orientation(self):
		return self.__orientation

	@orientation.setter
	def orientation(self, val):
		self.__orientation = val

	@property
	def site_rects(self):
		return self.__site_rects

	@site_rects.setter
	def site_rects(self, site_config):
		self.__site_rects = [None for i in xrange(9)]
		size = site_config[0]
		for i in xrange(1, 10):
			l = site_config[i][0] - size / 2
			r = site_config[i][0] + size / 2
			t = site_config[i][1] - size / 2
			b = site_config[i][1] + size / 2
			self.__site_rects[i - 1] = (l, t, r, b)

	@property
	def crop_rect(self):
		return self.__crop_rect

	@crop_rect.setter
	def crop_rect(self, crop_config):
		x = crop_config[0][0]
		y = crop_config[0][1]
		size = crop_config[1]
		l = x - size / 2
		r = x + size / 2
		t = y - size / 2
		b = y + size / 2
		self.__crop_rect = (l, t, r, b)

	@property
	def solve_to(self):
		return self.__solve_to

	@solve_to.setter
	def solve_to(self, pattern):
		self.__solve_to = pattern

	def scan_face(self):
		'''
		Gets image from camera, crops and gets average (mean) colors
		in each region, and stores in __raw_colors.
		Returns list of colors on this face for uix
		'''
		logo_threshold = 8

		face = FACES[self.__orientation[0]]
		rot = UP_FACE_ROT[self.__orientation]

		#get image from camera
		face_im = Image.open(testimages[face]) # TODO get camera instead of test images

		# crop the image to square
		img = face_im.crop(self.crop_rect)
		#im.show() # DEBUG

		#print 'Processing face', face, rot # DEBUG

		# loop through each site and store its raw color
		for sitenum in xrange(1, 10):
			abs_sitenum = ROT_TABLE[rot][sitenum - 1] # get unrotated site number
			site = img.crop(self.__site_rects[sitenum - 1]) # crop the img so only the site is left
			if self.__raw_colors[face][abs_sitenum - 1] is None: # if it hasn't already been set
				self.__raw_colors[face][abs_sitenum - 1] = ImageStat.Stat(site).mean # store the mean color in __raw_colors

		ret_colors = []
		for i in ROT_TABLE[rot]:
			ret_colors.append(self.__raw_colors[face][i - 1])
		return ret_colors # returns rotated list of raw_colors

	def get_solve_string(self):
		'''
		Gets the solve string
		'''
		return self.__solve_string

	def set_solve_string(self):
		'''
		Sets the solve string from kociemba
		'''
		#self.__solve_string = solve(self.__cube_def) # TODO allow solve to pattern also
		self.__solve_string = None

	def get_pos(self, servo_pin):
		'''
		Function to get current position of servo
		'''
		# TODO read input pin for servo position
		# pos = GPIO.input(servo_pin)
		pos = 90 # debug

		return pos

	def get_up_face(self):
		'''
		Returns string representing current up face
		'''
		return FACES_STR[FACE_POSITION[self.__orientation][U]]

	def get_up_rot(self):
		'''
		Returns current rotation of up_face
		'''
		return UP_FACE_ROT[self.__orientation]

	def get_up_raw_color(self, sitenum):
		'''
		Returns the raw color for site sitenum on upface
		'''
		sitenum = int(sitenum) - 1 # sites in range 0-8
		upface = FACES[self.get_up_face()]
		return self.__raw_colors[upface][sitenum]

	def set_up_raw_color(self, sitenum, rawcolor):
		'''
		Sets the raw color for site sitenum on upface. Sitenum needs to be transposed for upface rotation
		'''
		rot = UP_FACE_ROT[self.__orientation]
		rot_sitenum = int(sitenum) - 1 # sites in range 0-8
		sitenum = ROT_TABLE[rot][rot_sitenum] - 1
		upface = FACES[self.get_up_face()]
		self.__raw_colors[upface][sitenum] = rawcolor

	def grip(self, gripper, cmd):
		'''
		Function to open or close gripper
		gripper = 'A' or 'B'
		cmd = 'o' 'c' or 'l' for load
		'''
		temp = ''
		if cmd == 'o':
			temp = 'Open'
		elif cmd == 'c':
			temp = 'Close'
		elif cmd == 'l':
			temp = 'Load'

		self.__grip_state[gripper] = temp
		print temp, 'gripper', gripper

	def twist(self, gripper, dir):
		'''
		Function to twist gripper
		gripper = 'A' or 'B'
		dir = '+' 90-deg CW, '-' 90-deg CCW
		'''
		o = self.__orientation

		other_gripper = 'B' if gripper == 'A' else 'A'
		if self.__grip_state[gripper] == 'Load' or self.__grip_state[other_gripper] == 'Load': # don't twist if either gripper is in load position
			print 'Can\'t twist. Currently in load position'
			return
		if self.__grip_state[other_gripper] == 'Open': # other gripper is open, so this twist moves cube and changes orientation
			self.__orientation = NEW_ORIENTATION_TWISTA[o][dir] if gripper == 'A' else NEW_ORIENTATION_TWISTB[o][dir]
			print 'New orientation set to: %s' % self.__orientation
		print 'Twist gripper %s %s' % (gripper, dir)

	def move_face_for_twist(self, face_to_move, to_gripper = None):
		'''
		Will position face_to_move to gripper A or B depending on fewest moves.
		Moves face to chosen gripper, and updates cube orientation.
		If gripper passed as arg face_to_move will be positioned to input gripper.
		Returns chosen gripper
		'''
		moves = None
		o = self.__orientation
		print o

		# get current position of face to move
		face = FACE_POSITION[o][FACES[face_to_move]]
		print 'input face: %s face to move: %i' % (face_to_move, face)

		# get the moves to both gripper A and B so they can be compared
		moves_a = MOVES_TO_A[face].split(',')
		if moves_a[0] == '':
			moves_a = []
		moves_b = MOVES_TO_B[face].split(',')
		if moves_b[0] == '':
			moves_b = []

		# if a gripper was passed in as argument, move to that gripper
		if to_gripper == 'A':
			moves = moves_a
		elif to_gripper == 'B':
			moves = moves_b
		else: # else pick the least number of moves
			if len(moves_a) <= len(moves_b):
				moves = moves_a # moves to gripper A
				to_gripper = 'A'
			else:
				moves = moves_b # moves to gripper B
				to_gripper = 'B'
		print 'moving to %s' % to_gripper

		# perform the moves (if any)
		for move in moves:
			gripper_to_move = move[0]
			cmd = move[1]
			if cmd == '+' or cmd == '-': # if it's a twist command
				self.twist(gripper_to_move, cmd)
			else: # it must be a grip command
				self.grip(gripper_to_move, cmd)

		return to_gripper
