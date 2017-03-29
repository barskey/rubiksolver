U = 0
R = 1
F = 2
D = 3
L = 4
B = 5

cube_orientation = 'UFD'
# ----------------------------------------------------------------------
# Lookup table to store moves to get from given face to gripper A or B.
# Relative to cube in default position ordered URFDLB
# e.g. moves_to_A[D] would be the moves to get face in position D to gripper A
# 
# String is comma separated moves, with the following commands:
# Note: using lower case o and c so it doesn't look like 0
# A : Gripper A (front gripper)
# B : Gripper B (back gripper)
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

"""
Function to open or close Gripper
gripper = 'A' or 'B'
cmd = 'o' 'c' or 'l' for load
"""
def Grip(gripper, cmd):
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
def TwistGripper(gripper, dir):
	print 'Twist gripper', gripper, dir

"""
Transposes face by degrees given in orientation
face_string is array of colors
orientation is degrees of rotation
"""
def transpose(face_string, orientation):
	key = [0, 1, 2, 3, 4, 5, 6, 7, 8]
	if orientation == 0:
		key = [0, 1, 2, 3, 4, 5, 6, 7, 8]
	elif orientation == 90:
		key = [2, 5, 8, 1, 4, 7, 0, 3, 6]
	elif orientation == 180:
		key = [8, 7, 6, 5, 4, 3, 2, 1, 0]
	elif orientation == 270:
		key = [6, 3, 0, 7, 4, 1, 8, 5, 2]
	
	new_face = ['','','','','','','','','']
	for i in range(9):
		new_face[i] = face_string[key[i]]
	
	return ''.join(new_face)
		

def ReadFace(orientation):
	#read camera image and load values into array
	tempface = ['R','R','R','U','U','U','F','F','F']
	
	# translate array to correct for orientation
	newface = transpose(tempface, orientation)
	
	print 'Reading face at', orientation
	
	return newface

"""
After cube is insterted this will scan each side of the cube and build the definition string for solving.
Returns string ready for solve function
"""
def get_cube_def():
	global cube_orientation
	
	# Fully close both grippers
	Grip('A', 'c')
	Grip('B', 'c')
	
	UString = ReadFace(0)
	
	Grip('B', 'o')
	
	TwistGripper('A', '+')
	TwistGripper('A', '+')
	
	DString = ReadFace(180)
	
	TwistGripper('A', '+')
	Grip('B', 'c')
	Grip('A', 'o')
	TwistGripper('A', '-')
	Grip('A', 'c')
	
	RString = ReadFace(270)
	
	Grip('B', 'o')
	TwistGripper('A', '+')
	TwistGripper('A', '+')
	
	LString = ReadFace(90)
	
	Grip('B', 'c')
	Grip('A', 'o')
	TwistGripper('B', '+')
	Grip('A', 'c')
	Grip('B', 'o')
	TwistGripper('B', '-')
	TwistGripper('A', '+')
	Grip('B', 'c')
	Grip('A', 'o')
	TwistGripper('A', '-')
	Grip('A', 'c')
	
	BString = ReadFace(0)
	
	Grip('B', 'o')
	TwistGripper('A', '+')
	TwistGripper('A', '+')
	
	FString = ReadFace(0)
	
	Grip('B', 'c')
	
	cube_orientation = 'FDB'
	print 'Current orientation:', cube_orientation
	
	return (UString + RString + FString + DString + LString + BString)

	