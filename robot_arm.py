class RobotArm:
	def __init__(self, robot_id, fault=None):
		self.robot_id = robot_id
		self.fault = fault


		self.height = 0
		self.extension = 0


		self.box_in_storage = False
		self.gripper_active = False


		self.vertical_motor = False
		self.horizontal_motor = False
		self.grip_motor = False


		self.height_sensor = 0
		self.extension_sensor = 0
		self.grip_sensor = False
		self.weight_sensor = False

		self.rfid_reader = None		


	def stop_task(self, reason):
		self.vertical_motor = False
		self.horizontal_motor = False
		self.grip_motor = False


		print("\nFAILURE DETECTED:", reason)
		print("Module: Robot Arm")
		print("All motors stopped.")
		print("Robot reports FAILURE to WMS.")
		print(
			"Robot remains in its current stationary state. " \
			"Human intervention may be required."
		)


		raise RuntimeError(reason)




	def fetch_box(self, box_rfid, height, length):
		print("\n--- FETCH BOX OPERATION ---")


		# 1. Receive request from WMS
		print(f"WMS: Request received for box RFID {box_rfid}")


		# 2. Verify initial arm position
		print("\nChecking initial arm position...")
		if self.height_sensor != 0 or self.extension_sensor != 0:
			self.stop_task("Arm is NOT in retracted parked position")


		print("Height sensor:", self.height_sensor)
		print("Extension sensor:", self.extension_sensor)


		# 3. Raise arm to target height
		print("\nRaising arm...")
		self.vertical_motor = True
		print("Vertical motor: ON")
		if self.fault == "height":
			self.height_sensor = -1
		else:
			self.height = height
			self.height_sensor = height


		print("Height sensor:", self.height_sensor)
		if abs(self.height_sensor - height) > 0.01: # tolerance
			self.stop_task("Height sensor failure or incorrect positioning")


		self.vertical_motor = False
		print("Vertical motor: OFF")


		# 4. Extend arm to target length
		print("\nExtending arm...")
		self.horizontal_motor = True
		print("Horizontal motor: ON")
		if self.fault == "extension":
			self.extension_sensor = -1
		else:
			self.extension = length
			self.extension_sensor = length


		print("Extension sensor:", self.extension_sensor)
		if abs(self.extension_sensor - length) > 0.01:
			self.stop_task("Extension sensor failure or incorrect positioning")


		self.horizontal_motor = False
		print("Horizontal motor: OFF")


		# 5. Activate grip motor
		print("\nGripping box...")
		self.grip_motor = True
		print("Grip motor: ON")
		if self.fault == "grip":
			self.grip_sensor = False
		else:
			self.gripper_active = True
			self.grip_sensor = True


		print("Grip sensor:", self.grip_sensor)
		if not self.grip_sensor:
			self.stop_task("Grip motor failed to secure box")


		self.grip_motor = False
		print("Grip motor: OFF")


		# 6. Verify box RFID
		print("\nVerifying box identity...")
		if self.fault == "rfid":
			self.rfid_reader = None
		else:
			self.rfid_reader = box_rfid


		print("RFID reader:", self.rfid_reader)
		if self.rfid_reader != box_rfid:
			self.stop_task("Incorrect or missing RFID tag")


		print("Correct box identified.")


		# 7. Transfer box to robot storage
		print("\nTransferring box to storage...")
		self.box_in_storage = True
		if self.fault == "weight":
			self.weight_sensor = False
		else:
			self.weight_sensor = True


		print("Weight sensor:", self.weight_sensor)
		if not self.weight_sensor:
			self.stop_task("Weight sensor failed to detect box in storage")


		# 8. Release box
		print("\nReleasing box...")
		self.grip_motor = True
		self.gripper_active = False
		self.grip_sensor = False
		print("Grip sensor:", self.grip_sensor)
		self.grip_motor = False


		# 9. Retract arm
		print("\nRetracting arm...")
		self.horizontal_motor = True
		self.extension = 0
		self.extension_sensor = 0
		self.horizontal_motor = False
		print("Extension sensor:", self.extension_sensor)
		self.vertical_motor = True
		self.height = 0
		self.height_sensor = 0
		self.vertical_motor = False
		print("Height sensor:", self.height_sensor)


		# 10. Verify final arm position
		if self.height_sensor != 0 or self.extension_sensor != 0:
			self.stop_task("Arm failed to return to parked position")
		print("Arm successfully returned to parked position.")


		# 11. Notify WMS
		print("\nWMS: Box retrieval completed successfully.")
		return True



	def print_state(self):
		print("\n--- CURRENT ROBOT_ARM STATE ---")
		print("Height:", self.height)
		print("Extension:", self.extension)
		print("Box in storage:", self.box_in_storage)
		print("Gripper active:", self.gripper_active)
		print("Vertical motor:", self.vertical_motor)
		print("Horizontal motor:", self.horizontal_motor)
		print("Grip motor:", self.grip_motor)




# Main
if __name__ == "__main__":
# fault = None for normal exec
# available faults: height, extension, grip, rfid, weight.
	
	robot_arm = RobotArm(robot_id=69, fault=None)
	robot_arm.print_state() # can comment out if not needed, but thought it
	# would be nice to see the initial state before the operation.


	try:
		robot_arm.fetch_box(
			box_rfid=12345,
			height=1.2,
			length=0.6
		)


	except RuntimeError:
		print(
			"\nRobot arm operation failed due to a fault. " \
			"Please check the logs above for details."
		)
		pass


	robot_arm.print_state()