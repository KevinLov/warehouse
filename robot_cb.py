import threading
import time
from enum import Enum
from queue import Queue

'''
Hello Elena, 

To more readable code starts on row 50 for the robot
and on row 334 for the Conveyor belt.

For p+ we aimed to prove how our assertions prevented the hazards identified in task 1.
If you ctrl + f for "hazard", you will find the three points where we try to motivate why 
our implementation is safe

The arrows in the assertion is to help show what changed from the last state!
'''

class RobotController(threading.Thread):
	def __init__(self, robotqueue, cbqueue, robot_available = True, robot_sufficient_battery = True, id = 0):
		threading.Thread.__init__(self)
		self.robotqueue = robotqueue
		self.cbqueue = cbqueue
		self.available = robot_available
		self.sufficient_battery = robot_sufficient_battery
		self.location = "initial_location"
		self.in_waiting_area = False
		self.in_loading_area = False
		self.id = id
		# Assume some values here
		self.belt_collection_height = 1.0
		self.belt_collection_ext = 2.0
		self.valid_locations = ("initial_location", "waiting_area", "loading_area", "outside_scope")
		# Testing, True if testing these unexpected states (not empty)
		self.test_loading_area_empty = False
		self.test_waiting_area_empty = False
        # Robot HW motors
		self.mobile_base_motor_stopped      = True
		self.wheight_sensor_empty           = True
		self.arm_vertical_positions         = ("retracted", "pick-up", "pad-drop-off")
		self.arm_vertical_position          = ("retracted")
		self.arm_horisontal_positions       = ("retracted", "pick-up", "pad-drop-off")
		self.arm_horisontal_position        = ("retracted")
		self.rfid_reader                    = False
		self.grip_closed                    = True

	def run(self):
		self.fetch_box_from_collection_area(123)

	def print_state(self):
		print("\n--- CURRENT ROBOT CONTROLLER STATE ---")
		print("id: ", self.id)
		print("available: ", self.available)
		print("sufficient battery: ", self.sufficient_battery)
		print("location: ", self.location)

	def fetch_box_from_collection_area(self, box_rfid):
		# Robot is initially idle when it receives WMS command
		print("WMS command to fetch box from conveyor belt received")
		assert self.available and self.sufficient_battery
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == True

 
		# If robot not available
		if not (self.available and self.sufficient_battery):
			print("Robot cannot undergo task")
			print("Reported to WMS")
			return

		
		# Robot takes on misson and starts to move to waiting area when it is empty
		self.available = False
		while (not self.check_waiting_area_empty()): 
			time.sleep(1)
		self.move("waiting_area")
		assert self.mobile_base_motor_stopped == False            # <-----
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == True

		# Robot arrives in waiting area, awaiting synchronization with CB
		self.engage_brake()
		print("Robot at waiting area")
		self.in_waiting_area = True
		assert self.location 			      == "waiting_area"
		assert self.mobile_base_motor_stopped == True             # <----- 
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == True

		# Robot messages CB saying its ready and waits until it receives message from CB to move to, 
		# previous assertions shows that its ready and safe to move.
		self.robotqueue.put(("AtWaitingArea", self.id))

		# Wait for conveyor belt to ask Robot to enter loading area
		cbmessage = self.cbqueue.get()
		
		# Request should be to enter the loading area
		assert(cbmessage[0] == "RequestEnterLoadingArea" and cbmessage[1] == self.id)
		assert self.check_loading_area_empty()

		# Robot has received confirmation that loading area is empty 
		# With it a confirmation of robots id number, saying that the spot is reserved for it
		# If any other robot received message, they see its not for them and will not act. 
		# This prooves that we prevent hazard 1 from task 1 to occur
		print("Robot received request to enter loading area")
		self.move("loading_area")
		self.in_waiting_area = False
		print("Robot moving to loading area")
		time.sleep(0.2)
		assert cbmessage[1]                   == self.id
		assert self.location                  != "waiting_area"
		assert self.mobile_base_motor_stopped == False             # <----- 
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == True

        # Robot arrives at loading position in loading-area
		# Assert before notifying CB about readiness
		self.engage_brake()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True             # <----- 
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == True	
		
		# Notifying CB saying ready to receive box, not partaking in any actions until it receives instructions from CB
		self.robotqueue.put(("ReadyForLoading", self.id))


		# Wait for CB to have box ready
		cbmessage = self.cbqueue.get()

		
		# Message to robot should be to to fetch box and its dedicated to our desired robot
		assert(cbmessage[0] == "RequestFetchBoxFromConveyorBelt" and cbmessage[1] == self.id)
		print("Robot received request to fetch box from conveyor belt")
		
		
		# Robot starts box fetching sequence. It has already checked that it is ready to perform it
		# First open grip
		self.open_grip()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"
		assert self.arm_vertical_position     == "retracted"
		assert self.rfid_reader               == False
		assert self.grip_closed               == False	           # <----- 


		# Then height extension to prevent hazard number 3 in task 1.
		self.vertical_extension()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "retracted"       # <----- 
		assert self.arm_vertical_position     == "pick-up"
		assert self.rfid_reader               == False
		assert self.grip_closed               == False	

 
		# Then horizontal extension is performed
		self.horizontal_extension()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "pick-up"
		assert self.arm_vertical_position     == "pick-up"         # <----- 
		assert self.rfid_reader               == False
		assert self.grip_closed               == False	


		# Closing grip on box, preparing to move to loading pad
		self.close_grip_on_box()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == True
		assert self.arm_horisontal_position   == "pick-up"
		assert self.arm_vertical_position     == "pick-up"          
		assert self.rfid_reader               == True             # <-----
		assert self.grip_closed               == True	          # <-----


		# We engage pickup mechanism that places box on loading pad
		self.pick_up_procedure()
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == False            # <-----
		assert self.arm_horisontal_position   == "pad-drop-off"   # <-----
		assert self.arm_vertical_position     == "pad-drop-off"   # <-----       
		assert self.rfid_reader               == True             
		assert self.grip_closed               == False	          # <----- 

		self.retract_arms()   
		assert self.location                  == "loading_area"
		assert self.mobile_base_motor_stopped == True
		assert self.wheight_sensor_empty      == False            # <-----
		assert self.arm_horisontal_position   == "retracted"      # <-----
		assert self.arm_vertical_position     == "retracted"      # <-----       
		assert self.rfid_reader               == True             
		assert self.grip_closed               == True	          # <----- 		 

		# Notify CB that task is complete and move away. 
		# To prevent hazard nr. 2 in task 1 we ensure that robot is waiting 
		# for confirmation from CB that it received message, otherwise it will raise an error to WMS
		self.notify_and_move()   
		assert self.location                  != "loading_area"   # <-----
		assert self.mobile_base_motor_stopped == False            # <-----
		assert self.wheight_sensor_empty      == False            
		assert self.arm_horisontal_position   == "retracted"      
		assert self.arm_vertical_position     == "retracted"             
		assert self.rfid_reader               == True             
		assert self.grip_closed               == True	

		cbmessage = self.cbqueue.get()
		assert(cbmessage == ("AcknowledgeBoxFetch", self.id))
		print("CB acknowledges box fetched")
		print("Robot completed task successfully, has moved away")

	# Since we don't know any numerical coordinates in the warehouse, just use abstract locations for now
	def move(self, location):
		self.mobile_base_motor_stopped = False
		assert(location in self.valid_locations)
		self.location = location

	def engage_brake(self):
		self.mobile_base_motor_stopped = True
	
	def stop_task(self, reason):
		self.available = False

	def open_grip(self):
		self.grip_closed = False

	def vertical_extension(self):
		self.arm_vertical_position = "pick-up"

	def vertical_retraction(self):
		self.arm_vertical_position = "retracted"

	def horizontal_extension(self):
		self.arm_horisontal_position = "pick-up"

	def horizontal_retraction(self):
		self.arm_horisontal_position = "retracted"

	def pick_up_procedure(self):
		self.grip_closed             = False
		self.wheight_sensor_empty    = False
		self.arm_horisontal_position = "pad-drop-off"
		self.arm_vertical_position   = "pad-drop-off"

	def close_grip_on_box(self):
		self.grip_closed = True
		self.rfid_reader = True

	def retract_arms(self):
		self.grip_closed             = True
		self.arm_vertical_position   = "retracted"
		self.arm_horisontal_position = "retracted"

	def notify_and_move(self):
		print("Box successfully fetched by Robot")
		print("Notifying CB box fetched successfully")
		self.robotqueue.put(("ConveyorBeltNotifyBoxFetched", self.id))
		self.mobile_base_motor_stopped = False
		self.location                  = "moving"


	def check_loading_area_empty(self):
		if self.test_loading_area_empty:
			self.test_loading_area_empty = False
			print("Loading area not empty")
			time.sleep(1)
			return False
		
		print("Loading area confirmed empty")
		return True

	def check_waiting_area_empty(self):
		if self.test_waiting_area_empty:
			self.test_waiting_area_empty = False
			print("Waiting area not empty")
			time.sleep(1)
			return False
		
		print("Waiting area confirmed empty")
		return True

class ConveyorBeltController(threading.Thread):
	class BeltState(Enum):
		STOPPED = 1
		MOVING = 2

	class BoxLocation(Enum):
		INITIAL_POSITION = 1
		FETCH_POSITION = 2
		NOT_PRESENT = 3

	class LoadingBay(Enum):
		VACANT = 1
		OCCUPIED = 2
		DEPARTING = 3

	def __init__(self, cbqueue, robotqueue):
		threading.Thread.__init__(self)

		self.cbqueue = cbqueue
		self.robotqueue = robotqueue
		self.loading_bay_sensor = self.LoadingBay.VACANT
		self.expected_robot_id = None
		self.waiting_robot = None
		self.conveyor_belt_speed = self.BeltState.STOPPED
		self.box_sensor = self.BoxLocation.INITIAL_POSITION


	def run(self):
		self.conveyor_belt()

	def conveyor_belt(self):
		# Wait for loading area to be empty
		assert(self.conveyor_belt_speed == self.BeltState.STOPPED)
		while (self.loading_bay_sensor != self.LoadingBay.VACANT):
			time.sleep(1)	
		assert(self.loading_bay_sensor == self.LoadingBay.VACANT)
	
		# Wait for intial robot message
		robot_message = self.robotqueue.get()

		# Robot at waiting area
		if (robot_message[0] == "AtWaitingArea"):
			print("CB informed robot at waiting area")
			robot_id = robot_message[1]
			self.waiting_robot = robot_id
			assert(self.conveyor_belt_speed == self.BeltState.STOPPED)
			assert(self.loading_bay_sensor == self.LoadingBay.VACANT)
			assert(self.box_sensor == self.BoxLocation.INITIAL_POSITION)
			self.cbqueue.put(("RequestEnterLoadingArea", robot_id))
			self.expected_robot_id = robot_id
			self.waiting_robot = None
			time.sleep(0.2)		
		else: 
			self.inform_failure("Unexpected message received")

		robot_message = self.robotqueue.get()
		if (robot_message[0] == "ReadyForLoading"): 
			self.loading_bay_sensor = self.LoadingBay.OCCUPIED
			# CB has been informed robot is ready for loading, moving box
			assert(self.conveyor_belt_speed == self.BeltState.STOPPED)
			assert(self.box_sensor == self.BoxLocation.INITIAL_POSITION)
			assert(self.loading_bay_sensor == self.LoadingBay.OCCUPIED)
			assert(robot_message[1] == self.expected_robot_id)
			assert(self.waiting_robot == None)

			# CB moving box to fetching position
			self.start_belt()
			assert(self.conveyor_belt_speed == self.BeltState.MOVING)
			self.stop_belt_at_fetch_position()
			assert(self.conveyor_belt_speed == self.BeltState.STOPPED)

			# Box at fetching position
			assert(self.box_sensor == self.BoxLocation.FETCH_POSITION)
			assert(self.loading_bay_sensor == self.LoadingBay.OCCUPIED)

			# Robot informed Box can now fetched
			self.cbqueue.put(("RequestFetchBoxFromConveyorBelt", self.expected_robot_id))
			time.sleep(0.2)
		elif (robot_message[0] == "LoadingAreaOccupied"):
			print("Conveyor belt may have requested robot enter loading area when it was occupied")
			print("This has been reported to WMS, operations will continue")
			return

		robot_message = self.robotqueue.get()
		if (robot_message[0] == "ConveyorBeltNotifyBoxFetched" and robot_message[1] == self.expected_robot_id):
			self.box_sensor = self.BoxLocation.NOT_PRESENT
			self.loading_bay_sensor == self.LoadingBay.DEPARTING

			# Conveyor belt notified box fetched by robot
			self.loading_bay_sensor = self.LoadingBay.DEPARTING
			assert(self.box_sensor == self.BoxLocation.NOT_PRESENT)
			assert(robot_message[1] == self.expected_robot_id)
			assert(self.loading_bay_sensor == self.LoadingBay.DEPARTING)
			self.cbqueue.put(("AcknowledgeBoxFetch", robot_id))
			self.expected_robot_id = None
			self.box_sensor = self.BoxLocation.INITIAL_POSITION
			return


	def start_belt(self):
		self.conveyor_belt_speed = self.BeltState.MOVING

	def stop_belt_at_fetch_position(self):
		self.conveyor_belt_speed = self.BeltState.STOPPED
		self.box_sensor = self.BoxLocation.FETCH_POSITION

	def inform_failure(self, reason):
		print("FAILURE DETECTED", reason)
		print("Conveyor belt stopped")
		print("Conveyor belt reports FAILURE to WMS")
		print("Human intervention may be required")
		raise RuntimeError(reason)

# Main
if __name__ == "__main__":
	cbqueue = Queue()
	robotqueue = Queue()
	robot = RobotController(robotqueue, cbqueue)
	conveyor = ConveyorBeltController(cbqueue, robotqueue)
	robot.start()
	conveyor.start()
	robot.join()
	conveyor.join()

