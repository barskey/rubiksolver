#from kociemba import solve
from PIL import Image, ImageStat
#import RPi.GPIO as GPIO

PINS = {
	'twistA': 1,
	'gripA' : 2,
	'twistB': 3,
	'gripB' : 4
}

#Setup position pin GPIOs as inputs
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

THRESHOLD = 8 # used to determine how close a color (luminance) is

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

# Lookup table for new orientation after moving a face to gripper A or B when the cube is in the default position
# e.g. new_orientation_A[D] gives 'LDR', which the cube will be in after moving D to girpper A
NEW_ORIENTATION_A = ['RUL', 'URD', 'UFD', 'LDR', 'ULD', 'UBD']

NEW_ORIENTATION_B = ['DFU', 'LFR', 'BLF', 'UFD', 'RFL', 'FLB']

# Translate table to get from current orientation to representation as if in default position
# Order of faces is URFDLB - e.g. for face_position['RUL'], R is in default U, F is in default R, U is in default F, etc.
# so face_position['RUL'][L] gives face B in the default L position
FACE_POSITION = {
	'UFD': [U, R, F, D, L, B],
	'RUL': [R, F, U, L, B, D],
	'URD': [U, B, R, D, F, L],
	'LDR': [L, F, D, R, B, U],
	'ULD': [U, F, L, D, B, R],
	'UBD': [U, L, B, D, R, F],
	'DFU': [D, L, F, U, R, B],
	'LFR': [L, U, F, R, D, B],
	'BLF': [B, U, L, F, D, R],
	'RFL': [R, D, F, L, U, B],
	'FLB': [F, D, L, B, U, R]
}

# Lookup table for current rotation of up face when cube is in designated orientation
# degrees up face is rotated (CW) wrt looking at up face
UP_FACE_ROT = {
	'UFD': 0,
	'RUL': 180,
	'URD': 90,
	'LDR': 0,
	'ULD': 270,
	'UBD': 180,
	'DFU': 180,
	'LFR': 90,
	'BLF': 90,
	'RFL': 270,
	'FLB': 270
}

testimages = [
	'testimg/uface.jpg',
	'testimg/rface.jpg',
	'testimg/fface.jpg',
	'testimg/dface.jpg',
	'testimg/lface.jpg',
	'testimg/bface.jpg'
]

class MyCube():

	def __init__(self, sites, crop, grip_a, twist_a, grip_b, twist_b):
		self.__raw_colors = [[None for i in range(9)] for j in range(6)] # luminance for each raw color found on cube
		self.__norm_colors = [[None for i in range(9)] for j in range(6)] # letter representing normalized color for each site on cube
		self.__face_colors = [None for i in range(6)] # raw color of the center site on each face
		self.__logo_site = None # store location of site with logo
		self.__cube_def = None # string representing cube in order U1U2U3...R1...F1...etc
		self.__solve_string = None # intructions to solve cube
		
		self.twist_a_pos = self.get_pos('twistA')
		self.twist_b_pos = self.get_pos('twistB')
		self.grip_a_pos = self.get_pos('gripA')
		self.grip_b_pos = self.get_pos('gripB')
		
		self.site_rects = sites
		self.crop_rect = crop
		
		self.__orientation = 'UFD' # current orientation of the cube, Upface, gripper A Face, gripper B Face
	
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
	def site_rects(self, config_sites):
		self.__site_rects = [None for i in range(9)]
		for i in xrange(9):
			site = 'center' + str(i + 1)
			l = config_sites[site]['x'] - config_sites['size'] / 2
			r = config_sites[site]['x'] + config_sites['size'] / 2
			t = config_sites[site]['y'] - config_sites['size'] / 2
			b = config_sites[site]['y'] + config_sites['size'] / 2
			self.__site_rects[i] = (l, t, r, b)

	@property
	def crop_rect(self):
		return self.__crop_rect
	
	@crop_rect.setter
	def crop_rect(self, config_crop):
		l = config_crop['center_x'] - config_crop['size'] / 2
		r = config_crop['center_x'] + config_crop['size'] / 2
		t = config_crop['center_y'] - config_crop['size'] / 2
		b = config_crop['center_y'] + config_crop['size'] / 2
		self.__crop_rect = (l, t, r, b)
	
	"""
	This will rotate cube and scan each side to process each face
	"""
	def scan_faces(self):
		# Fully close both grippers
		self.grip('A', 'c')
		self.grip('B', 'c')

		self.process_face(U, 0)

		self.grip('B', 'o')

		self.twist('A', '+')
		self.twist('A', '+')

		self.process_face(D, 180)

		self.twist('A', '+')
		self.grip('B', 'c')
		self.grip('A', 'o')
		self.twist('A', '-')
		self.grip('A', 'c')

		self.process_face(R, 270)

		self.grip('B', 'o')
		self.twist('A', '+')
		self.twist('A', '+')

		self.process_face(L, 90)

		self.grip('B', 'c')
		self.grip('A', 'o')
		self.twist('B', '+')
		self.grip('A', 'c')
		self.grip('B', 'o')
		self.twist('B', '-')
		self.twist('A', '+')
		self.grip('B', 'c')
		self.grip('A', 'o')
		self.twist('A', '-')
		self.grip('A', 'c')

		self.process_face(B, 0)

		self.grip('B', 'o')
		self.twist('A', '+')
		self.twist('A', '+')

		self.process_face(F, 0)

		self.grip('B', 'c')

		self.__orientation = 'FDB'
		#print 'Current orientation:', self.orientation # DEBUG

	"""
	Gets image from camera, rotates as necessary, gets average (mean) colors
	in each region with probability, and stores in raw_colors
	"""
	def process_face(self, face, orientation):
		#get image from camera
		face_im = Image.open(testimages[face]) # DEBUG load test images instead

		# crop the image to square
		img = face_im.crop(self.__crop_rect)

		# rotate image as necessary so colors are records in correct order
		img = img.rotate(-orientation)
		#im.show() # DEBUG

		#print 'Processing face', face, orientation # DEBUG

		# loop through each site and store the color (luminance) found
		for i in range(9):
			site = img.crop((self.__site_rects[i]))
			# if the site has many colors, it must be a logo. Skip it and handle at the end
			if ImageStat.Stat(site).stddev[0] > 10 and ImageStat.Stat(site).stddev[1] > 10 and ImageStat.Stat(site).stddev[2] > 10:
				print 'face: %s site: %s' % (face, i)
				self.__logo_site = [face, i]
			else:
				self.__raw_colors[face][i] = ImageStat.Stat(site).mean

	"""
	Loops through raw_colors and tries to identify and assign face colors
	"""
	def guess_colors(self):

		# start by assigning the center color[4] to the face_colors list.
		for face, colors in enumerate(self.__raw_colors):
			if colors[4]: # Skip if it is none - must be logo site
				self.__face_colors[face] = colors[4]

		# If there is a logo site, check the remaining face_colors for a missing one
		missing_face = None
		if self.__logo_site:
			missing_face = self.__face_colors.index(None)
		print FACES_STR[missing_face] # Debug

		# check every site on the cube for a good match for the missing color
		for face, colors in enumerate(self.__raw_colors): # for each face on the cube
			for site, color in enumerate(colors): # for each color on this face
				# compare to each color in the colors list to check for a close enough match
				try_color = []
				for face_color in self.__face_colors:
					if face_color is not None and color is not None:
						if not self.is_similar(color, face_color, THRESHOLD):
							try_color.append(color)
		print try_color
		if missing_face:
			self.__face_colors[missing_face] = try_color[0]

		# then check if each color is within a certain tolerance of face colors for assignment
		for face, colors in enumerate(self.__raw_colors): # for each face on the cube
			for site, color in enumerate(colors): # for each color on this face
				# compare to each color in the colors list to check for a close enough match
				match = False
				for face_color in self.__face_colors:
					if self.is_similar(color, face_color, THRESHOLD):
						self.__norm_colors[face][site] = FACES_STR[face]
						match = True
				if not match:
					print 'Could not find a match for face: %s, site: %s, lum: %s' % (face, site, color)
	"""
	Gets the solve string
	"""
	def get_solve_string(self):
		return self.__solve_string
		
	"""
	Sets the solve string from kociemba
	"""
	def set_solve_string(self):
		#self.__solve_string = solve(self.__cube_def) # TODO allow solve to pattern also
		self.__solve_string = None

	"""
	Function to get current position of servo
	"""
	def get_pos(self, servo_pin):
		# TODO read input pin for servo position
		# pos = GPIO.input(servo_pin)
		pos = 90 # debug
		
		return pos

	def get_up_face(self):
		return FACES_STR[FACE_POSITION[self.__orientation][U]]
	
	def get_up_rot(self):
		return UP_FACE_ROT[self.__orientation]
	
	"""
	Function to open or close gripper
	gripper = 'A' or 'B'
	cmd = 'o' 'c' or 'l' for load
	"""
	def grip(self, gripper, cmd):
		temp = ''
		if cmd == 'o':
			temp = 'Open'
		elif cmd == 'c':
			temp = 'Close'
		elif cmd == 'l':
			temp = 'Load'
			
		print temp, 'gripper', gripper

	"""
	Function to twist gripper
	gripper = 'A' or 'B'
	dir = '+' 90-deg CW, '-' 90-deg CCW
	"""
	def twist(self, gripper, dir):
		print 'Twist gripper', gripper, dir
		
	"""
	Decides which gripper to move face to, based on the fewest moves
	Moves face to chosen gripper, and updates cube orientation
	Returns chosen gripper
	"""
	def move_face_for_twist(self, face_to_move):
		moves = None
		orientation = self.__orientation
		gripper = None
		
		face = FACES[face_to_move]
		
		moves_a = MOVES_TO_A[face].split(',')
		if moves_a[0] == '':
			moves_a = []
		moves_b = MOVES_TO_B[face].split(',')
		if moves_b[0] == '':
			moves_b = []
		print moves_a, moves_b
		# pick the least number of moves
		if len(moves_a) <= len(moves_b): # move face to gripper A
			moves = moves_a
			orientation = NEW_ORIENTATION_A[face]
			gripper = 'A'
		else: # move face to gripper b
			moves = moves_b
			orientation = NEW_ORIENTATION_B[face]
			gripper = 'B'
			
		for move in moves:
			gripper = move[0]
			cmd = move[1]
			if cmd == '+' or cmd == '-': # if it's a twist command
				self.twist(gripper, cmd)
			else: # it must be a grip command
				self.grip(gripper, cmd)
		
		self.__orientation = orientation
		
		return gripper
		
	
	def luminance(pixel):
		return (0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])

	def is_similar(a, b, threshold):
		return abs(self.luminance(a) - self.luminance(b)) < threshold
