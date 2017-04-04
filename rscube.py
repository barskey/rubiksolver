from kociemba import solve
from PIL import Image, ImageStat

U = 0
R = 1
F = 2
D = 3
L = 4
B = 5

faces = ['U', 'R', 'F', 'D', 'L', 'B']

THRESHOLD = 8 # used to determine how close a color (luminance) is

# ----------------------------------------------------------------------
# Lookup table to store moves to get from given face to gripper A or B.
# Relative to cube in default position ordered URFDLB
# e.g. moves_to_A[D] would be the moves to get face in position D to gripper A
#
# String is comma separated moves, with the following commands:
# Note: using lower case o and c so it doesn't look like 0
# A : gripper A (front gripper)
# B : gripper B (back gripper)
# o : Open
# c : Close
# + : Clockwise turn
# - : Counter-clockwise turn
moves_to_A = [
	'Bo,A-,Bc,Ao,B+,A+,Ac,Bo,B-,Bc', 'Ao,B-,Ac,Bo,B+,Bc', '', 'Bo,A+,Bc,Ao,B+,A-,Ac,Bo,B-,Bc', 'Ao,B+,Ac,Bo,B-,Bc', 'Ao,B+,B+,Ac'
]

moves_to_B = [
	'Bo,A+,A+,Bc', 'Bo,A+,Bc,Ao,A-,Ac', 'Ao,B+,Ac,Bo,B-,A+,Bc,Ao,A-,Ac', '', 'Bo,A-,Bc,Ao,A+,Ac', 'Ao,B+,Ac,Bo,B-,A-,Bc,Ao,A+,Ac'
]

# Lookup table for new orientation after moving a face to gripper A or B when the cube is in the default position
# e.g. new_orientation_A[D] gives 'LDR', which the cube will be in after moving D to girpper A
new_orientation_A = ['RUL', 'URD', 'UFD', 'LDR', 'ULD', 'UBD']

new_orientation_B = ['DFU', 'LFR', 'BLF', 'UFD', 'RFL', 'FLB']

# Translate table to get from current orientation to representation as if in default position
# Order of faces is URFDLB - e.g. for face_position['RUL'], R is in default U, F is in default R, U is in default F, etc.
# so face_position['RUL'][L] gives face B in the default L position
face_position = {
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

# Coordinates of nine sites to measure average colors on cube in 4-tuple (left, upper, right, lower)
# Assumes 640x480 image, PIL uses 0,0 in upper left
sites = [
	(10,  10,  70,  70),
	(130, 10,  190, 70),
	(250, 10,  310, 70),
	(10,  120, 70,  180),
	(130, 120, 190, 180),
	(250, 120, 310, 180),
	(10,  250, 70,  310),
	(130, 250, 190, 310),
	(250, 250, 310, 310)
]

testimages = [
	'testimg/uface.jpg',
	'testimg/rface.jpg',
	'testimg/fface.jpg',
	'testimg/dface.jpg',
	'testimg/lface.jpg',
	'testimg/bface.jpg'
]

class MyCube():

	def __init__(self):
		self.raw_colors = [[None for i in range(9)] for j in range(6)] # luminance for each raw color found on cube
		self.norm_colors = [[None for i in range(9)] for j in range(6)] # letter representing normalized color for each site on cube
		self.face_colors = [None for i in range(6)] # raw color of the center site on each face
		self.logo_site = None # store location of site with logo
		self.orientation = 'UFD' # current orientation of the cube, Upface, gripper A Face, gripper B Face
		self.cube_def = None # string representing cube in order U1U2U3...R1...F1...etc
		self.solve_string = None # intructions to solve cube

	"""
	This will rotate cube and scan each side to process each face
	"""
	def scan_faces(self):
		# Fully close both grippers
		grip('A', 'c')
		grip('B', 'c')

		self.process_face(U, 0)

		grip('B', 'o')

		twist_gripper('A', '+')
		twist_gripper('A', '+')

		self.process_face(D, 180)

		twist_gripper('A', '+')
		grip('B', 'c')
		grip('A', 'o')
		twist_gripper('A', '-')
		grip('A', 'c')

		self.process_face(R, 270)

		grip('B', 'o')
		twist_gripper('A', '+')
		twist_gripper('A', '+')

		self.process_face(L, 90)

		grip('B', 'c')
		grip('A', 'o')
		twist_gripper('B', '+')
		grip('A', 'c')
		grip('B', 'o')
		twist_gripper('B', '-')
		twist_gripper('A', '+')
		grip('B', 'c')
		grip('A', 'o')
		twist_gripper('A', '-')
		grip('A', 'c')

		self.process_face(B, 0)

		grip('B', 'o')
		twist_gripper('A', '+')
		twist_gripper('A', '+')

		self.process_face(F, 0)

		grip('B', 'c')

		self.orientation = 'FDB'
		#print 'Current orientation:', self.orientation # DEBUG

	"""
	Gets image from camera, rotates as necessary, gets average (mean) colors
	in each region with probability, and stores in raw_colors
	"""
	def process_face(self, face, orientation):
		#get image from camera
		face_im = Image.open(testimages[face]) # DEBUG load test images instead

		# crop the image to square
		img = face_im.crop((160, 80, 480, 400))

		# rotate image as necessary so colors are records in correct order
		img = img.rotate(-orientation)
		#im.show() # DEBUG

		#print 'Processing face', face, orientation # DEBUG

		# loop through each site and store the color (luminance) found
		for i in range(9):
			site = img.crop((sites[i]))
			# if the site has many colors, it must be a logo. Skip it and handle at the end
			if ImageStat.Stat(site).stddev[0] > 10 and ImageStat.Stat(site).stddev[1] > 10 and ImageStat.Stat(site).stddev[2] > 10:
				print 'face: %s site: %s' % (face, i)
				self.logo_site = [face, i]
			else:
				self.raw_colors[face][i] = ImageStat.Stat(site).mean

	"""
	Loops through raw_colors and tries to identify and assign face colors
	"""
	def guess_colors(self):

		# start by assigning the center color[4] to the face_colors list.
		for face, colors in enumerate(self.raw_colors):
			if colors[4]: # Skip if it is none - must be logo site
				self.face_colors[face] = colors[4]

		# If there is a logo site, check the remaining face_colors for a missing one
		missing_face = None
		if self.logo_site:
			missing_face = self.face_colors.index(None)
		print faces[missing_face] # Debug

		# check every site on the cube for a good match for the missing color
		for face, colors in enumerate(self.raw_colors): # for each face on the cube
			for site, color in enumerate(colors): # for each color on this face
				# compare to each color in the colors list to check for a close enough match
				try_color = []
				for face_color in self.face_colors:
					if face_color is not None and color is not None:
						if not is_similar(color, face_color, THRESHOLD):
							try_color.append(color)
		print try_color
		if missing_face:
			self.face_colors[missing_face] = try_color[0]

		# then check if each color is within a certain tolerance of face colors for assignment
		for face, colors in enumerate(self.raw_colors): # for each face on the cube
			for site, color in enumerate(colors): # for each color on this face
				# compare to each color in the colors list to check for a close enough match
				match = False
				for face_color in self.face_colors:
					if is_similar(color, face_color, THRESHOLD):
						self.norm_colors[face][site] = faces[face]
						match = True
				if not match:
					print 'Could not find a match for face: %s, site: %s, lum: %s' % (face, site, color)
	"""
	Gets the solve string from kociemba
	"""
	def get_solve_string(self):
		self.solve_string = solve(self.cube_def)

"""
Function to open or close gripper
gripper = 'A' or 'B'
cmd = 'o' 'c' or 'l' for load
"""
def grip(gripper, cmd):
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
def twist_gripper(gripper, dir):
	print 'Twist gripper', gripper, dir

def luminance(pixel):
	return (0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])

def is_similar(a, b, threshold):
    return abs(luminance(a) - luminance(b)) < threshold
