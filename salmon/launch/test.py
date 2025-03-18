#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped, Pose, Twist
from move_base_msgs.msg import MoveBaseActionResult
from std_msgs.msg import Header, String
import os
from json import load
from copy import deepcopy
from time import sleep

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Nav():

    JSON_KEY_POSITION = "position"
    JSON_KEY_ORIENTATION = "orientation"
    JSON_KEY_NEIGHBOURS = "neighbours"
    KEY_NAME = "name"
    JSON_KEY_ACTIONS = "actions"
    JSON_KEY_ACTION = "action"
    ACTION_REVERSE = "reverse"
    JSON_KEY_WHEN = "when"
    ACTION_WHEN_DEPARTURE = "departure"
    JSON_KEY_DURATION = "duration"

    def __init__(self, waypoints_file, starting_waypoint ="start"):
        
        with open(waypoints_file,"r") as file:
            self.waypoints =  load(file)

        self.current_waypoint = starting_waypoint
    
    def navigate_to_waypoint(self, target):
        """
        Returns a list of poses to pass through to reach the target
        """

        assert target in self.waypoints.keys(), f"Waypoint {target} hasn't been defined"

        path: list = self.get_path_to_waypoint(start=self.current_waypoint, target=target, path=[])

        assert path is not None or len(path) == 0, f"No path to {target}"
        
        self.current_waypoint = target

        # Translate the list of waypoints to a list of poses for the robot to go to
        poses = []
        for waypoint in path:
            pose = deepcopy(self.waypoints[waypoint])
            pose[Nav.KEY_NAME] = waypoint
            pose.pop(Nav.JSON_KEY_NEIGHBOURS)
            poses.append(pose)

        return poses
    
    def get_path_to_waypoint(self,
                             start,
                             target,
                             path = []
                             ):
        """
        Returns a list of waypoints to pass through to reach the target.
        Returns None if target is unreachable. Function is recursive and checks
        every possible path so will not scale well with lots of waypoints.
        """

        path.append(start)
        return_path = []
        current_neighbours = self.waypoints[start][Nav.JSON_KEY_NEIGHBOURS]

        # Trivial case
        if start == target:
            return_path = path
        
        # Target next to start
        elif target in current_neighbours:
            path.append(target)
            return_path = path
        
        # Target further away
        else:
            
            # Make sure we don't go to the same waypoint twice
            filtered_neighbours = [waypoint for waypoint in current_neighbours if waypoint not in path]

            # Dead end
            if filtered_neighbours == []:
                return_path = None
            
            # Not a dead end: find all paths from neighbours to target
            for next_waypoint in filtered_neighbours:

                # Select the shortest path
                possible_path = self.get_path_to_waypoint(start=next_waypoint, target=target, path=deepcopy(path))
                if possible_path is not None and ((len(possible_path) < len(return_path)) or return_path == []):
                    return_path = possible_path
        
        if return_path == []:
            return_path = None
        return return_path


waypoints_dir = os.path.abspath("src/magni_robot/salmon/waypoints/positions.json")
nav = Nav(waypoints_file=waypoints_dir, starting_waypoint="start")

goal_reached = False
waypoints_list = []

def statusCallback(data):
    status = data.status.status
    global goal_reached
    if status==3:
        goal_reached = True
    else:
        goal_reached = False

def waypointCallback(data):
    global waypoints_list
    target_waypoint = data.data
    print(f"Target recieved: {target_waypoint}")
    print(f"Current waypoint is {nav.current_waypoint}")
    waypoints_list=nav.navigate_to_waypoint(target_waypoint)
    
def reverse(publisher, duration, speed=0.2, cmd_topic_hz=20):
    print(f"Reversing for {duration}s at {speed}m/s")
    t = Twist()
    t.linear.x = -abs(speed if speed <= 0.2 else 0.2)
    t.linear.y = 0
    t.linear.z = 0
    t.angular.x = 0
    t.angular.y = 0
    t.angular.z = 0
    rate = rospy.Rate(cmd_topic_hz)
    for i in range(int(duration*cmd_topic_hz)):
        publisher.publish(t)
        rate.sleep()
    t.linear.x = 0
    publisher.publish(t)

def publishPose(publisher, pose):
    h = Header()
    h.stamp = rospy.Time.now()
    h.frame_id = pose['frame_id']
    p = Pose()
    p.position.x = pose['position']['x']
    p.position.y = pose['position']['y']
    p.position.z = pose['position']['z']
    p.orientation.x = pose['orientation']['x']
    p.orientation.y = pose['orientation']['y']
    p.orientation.z = pose['orientation']['z']
    p.orientation.w = pose['orientation']['w']
    message = PoseStamped(h,p)
    publisher.publish(message)

def publish_finished(publisher):
    s = String()
    s.data = "SALMON Move finished"
    publisher.publish(s)


def talker():
    global goal_reached
    global waypoints_list
    pub_goal = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
    sub = rospy.Subscriber('/move_base/result', MoveBaseActionResult, statusCallback)

    # Used for reversing
    pub_cmd_velocity = rospy.Publisher('/cmd_vel', Twist)
    
    pub_finished = rospy.Publisher('/salmon/finished', String, queue_size=10)
    subWaypoint = rospy.Subscriber('/salmon/goal_waypoint', String, waypointCallback)

    rospy.init_node('PoseConductor', anonymous=True)
    rate = rospy.Rate(0.1)

    while not rospy.is_shutdown():

        if goal_reached and waypoints_list:
            print(f"Current waypoint is {nav.current_waypoint}")

            # Implement actions on depature
            if len(waypoints_list) > 1 and Nav.JSON_KEY_ACTIONS in waypoints_list[0].keys():
                actions = [action for action in waypoints_list[0][Nav.JSON_KEY_ACTIONS] if action[Nav.JSON_KEY_WHEN] == Nav.ACTION_WHEN_DEPARTURE]
                for action_struct in actions:
                    action = action_struct[Nav.JSON_KEY_ACTION]
                    if action == Nav.ACTION_REVERSE:
                        reverse(publisher=pub_cmd_velocity,
                                duration=action_struct[Nav.JSON_KEY_DURATION])
            
            waypoints_list.remove(waypoints_list[0])
            try:
                print(f"Goal Reached, going to next waypoint: {waypoints_list[0][Nav.KEY_NAME]}")
            except:
                print(bcolors.OKGREEN + "Move finished" + bcolors.ENDC)
                publish_finished(pub_finished)
                print("sent finished message")
                
            goal_reached = False
        if waypoints_list:
            current_waypoint = waypoints_list[0]

            

            publishPose(pub_goal, current_waypoint)
        rate.sleep()






if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass