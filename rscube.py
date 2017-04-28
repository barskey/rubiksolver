#from kociemba import solve
from PIL import Image, ImageStat
import time
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
	'DLU': [D, B, L, U, F, R],
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

PATTERNS = [
	['Checkerboard',         'checkerboard.jpg',             'UFUFUFUFURURURURURFRFRFRFRFDBDBDBDBDLDLDLDLDLBLBLBLBLB'],
	['Easy Checkerboard',    'easy-checkerboard.jpg',        'UDUDUDUDURLRLRLRLRFBFBFBFBFDUDUDUDUDLRLRLRLRLBFBFBFBFB'],
	['Wire',                 'wire.jpg',                     'UUUUUUUUURLLRRRLLRBBFFFFFBBDDDDDDDDDLRRLLLRRLFFBBBBBFF'],
	['Tablecloth',           'tablecloth.jpg',               'BFBRURBFBRURURURURURUBFBURUFBFLDLFBFLDLDLDLDLDLDFBFDLD'],
	['Spiral',               'spiral.jpg',                   'FFFFUFFUURRUURUUUURRFRFFRRRBBBBDBDDBDDDDLDLLDLLLLBBLLB'],
	['Vertical Stripes',     'vertical-stripes.jpg',         'UUUUUUUUUBRFBRFBRFLFRLFRLFRDDDDDDDDDFLBFLBFLBRBLRBLRBL'],
	['Opposite Corners',     'opposite-corners.jpg',         'DDDDUDDDDLRRRRRRRLBFFFFFFFBUUUUDUUUURLLLLLLLRFBBBBBBBF'],
	['Cross',                'cross.jpg',                    'DUDUUUDUDFRFRRRFRFRFRFFFRFRUDUDDDUDUBLBLLLBLBLBLBBBLBL'],
	['Cross 2',              'cross2.jpg',                   'RURUUURURFRFRRRFRFUFUFFFUFULDLDDDLDLBLBLLLBLBDBDBBBDBD'],
	['Cube in cube',         'cube-in-cube.jpg',             'FFFFUUFUURRURRUUUURFFRFFRRRBBBDDBDDBDDDLLDLLDLLLLBBLBB'],
	['Cube in cube in cube', 'cube-in-a-cube-in-a-cube.jpg', 'RRRRUURUFURFRRFFFFUFRUFFUUULLLDDLBDLBBBLLBDLBDDDDBBDBL'],
	['Anaconda',             'anaconda.jpg',                 'FUFUUFFFFUUUURRURURRRFFRRFRBDBBDDBBBDLDDLLDDDLBLBBLLLL'],
	['Python',               'python.jpg',                   'DUDDUDDUDFFFFRRFRFRFRFFRRRRUUUDDDUUUBBBBLLBLBLBLBBLLLL'],
	['Black Mamba',          'black-mamba.jpg',              'RURUURRRRBBBRRRBBBDDDFFFDDDLLLDDLLDLFLFFLLFFFUBUUBUUBU'],
	['Green Mamba',          'green-mamba.jpg',              'RRRUUURRRBBBRRRBBBDDDFFFDDDLLLDDLLDLFLFFLLFFFUUUBBUUBU'],
	['Four Spots',           'four-spots.jpg',               'UUUUUUUUULLLLRLLLLBBBBFBBBBDDDDDDDDDRRRRLRRRRFFFFBFFFF'],
	['Six Spots',            'six-spots.jpg',                'FFFFUFFFFUUUURUUUURRRRFRRRRBBBBDBBBBDDDDLDDDDLLLLBLLLL'],
	['Twister',              'twister.jpg',                  'RURRUURUURRFRRFFRFUFFFFFUUULLLDDDDDLBBBLLLLLBDBDDBBDBB'],
	['Center Edge Corner',   'center-edge-corner.jpg',       'RFRFUFRFRFUFURUFUFURURFRURULBLBDBLBLBDBDLDBDBDLDLBLDLD'],
	['Tetris',               'tetris.jpg',                   'FFBFUBFBBUDDURDUUDRLLRFLRRLBBFBDFBFFUDDULDUUDLRRLBRLLR'],
	['Facing Checkerboards', 'facing-checkerboards.jpg',     'UUUUUUUUURLRLRLRLRFFFFFFFFFDDDDDDDDDLRLRLRLRLBBBBBBBBB']
]

class MyCube(object):

	def __init__(self, site_center_x, site_center_y, site_size, crop_center, crop_size, grip_a, twist_a, grip_b, twist_b):
		self._raw_colors = [[None for i in range(9)] for j in range(6)] # r, g, b for each raw color found on cube
		self._face_colors = [None for i in range(6)] # matched color of the center site on each face
		self._match_colors = [[None for i in range(9)] for j in self._face_colors] # matched color for each site
		self._cube_colors = [[None for i in range(9)] for j in self._face_colors] # letter for corresponding face_color for each site on cube
		self.solve_to = None # string representing cube solve pattern, None to solve to standard
		self._solve_string = None # instructions to solve cube

		self._grip_state = {'A': None, 'B': None}

		site_list = [None for i in range(10)] # site_rects expects list of 10, 0 is size, 1-9 are (x,y) tuples
		site_list[0] = site_size
		for i in range(9):
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
		return self._orientation

	@orientation.setter
	def orientation(self, val):
		self._orientation = val

	@property
	def site_rects(self):
		return self._site_rects

	@site_rects.setter
	def site_rects(self, site_config):
		self._site_rects = [None for i in range(9)]
		size = site_config[0]
		for i in range(1, 10):
			l = site_config[i][0] - size / 2
			r = site_config[i][0] + size / 2
			t = site_config[i][1] - size / 2
			b = site_config[i][1] + size / 2
			self._site_rects[i - 1] = (l, t, r, b)

	@property
	def crop_rect(self):
		return self._crop_rect

	@crop_rect.setter
	def crop_rect(self, crop_config):
		x = crop_config[0][0]
		y = crop_config[0][1]
		size = crop_config[1]
		l = x - size / 2
		r = x + size / 2
		t = y - size / 2
		b = y + size / 2
		self._crop_rect = (l, t, r, b)

	@property
	def solve_to(self):
		return self._solve_to

	@solve_to.setter
	def solve_to(self, pattern):
		self._solve_to = pattern

	def scan_face(self):
		"""
		Gets image from camera, crops and gets average (mean) colors
		in each region, and stores in _raw_colors.
		Returns list of colors on this face for uix
		"""
		logo_threshold = 8

		face = FACES[self._orientation[0]]
		rot = UP_FACE_ROT[self._orientation]

		#get image from camera
		face_im = Image.open(testimages[face]) # TODO get camera instead of test images

		# crop the image to square
		img = face_im.crop(self.crop_rect)
		#im.show() # DEBUG

		#print 'Processing face', face, rot # DEBUG

		# loop through each site and store its raw color
		for sitenum in range(1, 10):
			abs_sitenum = ROT_TABLE[rot][sitenum - 1] # get unrotated site number
			site = img.crop(self._site_rects[sitenum - 1]) # crop the img so only the site is left
			if self._raw_colors[face][abs_sitenum - 1] is None: # if it hasn't already been set
				self._raw_colors[face][abs_sitenum - 1] = ImageStat.Stat(site).mean # store the mean color in _raw_colors

		ret_colors = []
		for i in ROT_TABLE[rot]:
			ret_colors.append(self._raw_colors[face][i - 1])
		return ret_colors # returns rotated list of raw_colors
		
	def get_abs_site(self, site_r):
		"""
		Transposes site numbers given up_face rotation. Returns unrotated site number given rotated site.
		"""
		return ROT_TABLE[UP_FACE_ROT[self._orientation]][site_r - 1]
	
	def set_face_color(self, f, color):
		"""
		Sets face color of face f
		"""
		face = str(f)
		if not face.isdigit():
			face = FACES[face]
		self._face_colors[face] = color
	
	def get_solve_string(self):
		"""
		Gets the solve string
		"""
		return self._solve_string

	def set_solve_string(self):
		"""
		Sets the solve string from kociemba
		"""
		cubedef = self.get_cube_def()
		print self._cube_colors, cubedef
		#self._solve_string = solve(cube_def) # TODO allow solve to pattern also
		self._solve_string = ''
		return 0
		
	def set_cube_colors(self):
		"""
		Sets each site to letter representing face color
		"""
		for f in range(6):
			for s in range(9):
				self._cube_colors[f][s] = FACES_STR[self._face_colors.index(self._match_colors[f][s])]
		print self._cube_colors
	
	def get_cube_def(self):
		"""
		Returns cube_def in the form UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
		"""
		return ''.join(str(site) for sitelist in self._cube_colors for site in sitelist)

	def get_pos(self, servo_pin):
		"""
		Function to get current position of servo
		"""
		# TODO read input pin for servo position
		# pos = GPIO.input(servo_pin)
		pos = 90 # debug

		return pos

	def get_up_face(self):
		"""
		Returns string representing current up face
		"""
		return FACES_STR[FACE_POSITION[self._orientation][U]]

	def get_up_rot(self):
		"""
		Returns current rotation of up_face
		"""
		return UP_FACE_ROT[self._orientation]

	def get_up_raw_color(self, site_r):
		"""
		Returns the raw color for site site_r on upface. Transposes if necessary for rotated face
		"""
		sitenum = int(site_r)
		upface = FACES[self.get_up_face()]
		s = self.get_abs_site(sitenum)
		return self._raw_colors[upface][s - 1]

	def set_up_raw_color(self, site_r, rawcolor):
		"""
		Sets the raw color for site site_r on upface. site_r needs to be transposed for upface rotation
		"""
		sitenum = self.get_abs_site(int(site_r))
		upface = FACES[self.get_up_face()]
		self._raw_colors[upface][sitenum - 1] = rawcolor
		
	def set_up_match_color(self, site_r, color):
		"""
		Sets matched color on up_face for given (possibly) rotated site_r
		"""
		upface = FACES[self.get_up_face()]
		s = self.get_abs_site(site_r)
		self._match_colors[upface][s - 1] = color

	def grip(self, gripper, cmd):
		"""
		Function to open or close gripper
		gripper = 'A' or 'B'
		cmd = 'o' 'c' or 'l' for load
		"""
		temp = ''
		if cmd == 'o':
			temp = 'Open'
		elif cmd == 'c':
			temp = 'Close'
		elif cmd == 'l':
			temp = 'Load'

		self._grip_state[gripper] = temp
		print '%s gripper %s' % (temp, gripper)

	def twist(self, gripper, dir):
		"""
		Function to twist gripper
		gripper = 'A' or 'B'
		dir = '+' 90-deg CW, '-' 90-deg CCW
		"""
		o = self._orientation

		other_gripper = 'B' if gripper == 'A' else 'A'
		if self._grip_state[gripper] == 'Load' or self._grip_state[other_gripper] == 'Load': # don't twist if either gripper is in load position
			print 'Can\'t twist. Currently in load position'
			return
		if self._grip_state[other_gripper] == 'Open': # other gripper is open, so this twist moves cube and changes orientation
			self._orientation = NEW_ORIENTATION_TWISTA[o][dir] if gripper == 'A' else NEW_ORIENTATION_TWISTB[o][dir]
		print 'Twist gripper %s %s Orientation: %s' % (gripper, dir, self._orientation)

	def move_face_for_twist(self, face_to_move, to_gripper = None):
		"""
		Will position face_to_move to gripper A or B depending on fewest moves.
		Moves face to chosen gripper, and updates cube orientation.
		If gripper passed as arg face_to_move will be positioned to input gripper.
		Returns chosen gripper
		"""
		moves = None
		o = self._orientation
		print o

		# get current position of face to move
		face = FACE_POSITION[o].index(FACES[face_to_move])

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
		print 'Moving face %i to gripper %s' % (face, to_gripper)

		# perform the moves (if any)
		for move in moves:
			gripper_to_move = move[0]
			cmd = move[1]
			if cmd == '+' or cmd == '-': # if it's a twist command
				self.twist(gripper_to_move, cmd)
			else: # it must be a grip command
				self.grip(gripper_to_move, cmd)

		return to_gripper
