#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion
from move_base_msgs.msg import MoveBaseActionResult
from std_msgs.msg import Header, String
import os
from json import load
from copy import deepcopy

class Nav():

    JSON_KEY_POSITION = "position"
    JSON_KEY_ORIENTATION = "orientation"
    JSON_KEY_NEIGHBOURS = "neighbours"

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
            pose["name"] = waypoint
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
    

def publishPose(pose, publisher):
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

def talker():
    global goal_reached
    global waypoints_list
    pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
    sub = rospy.Subscriber('/move_base/result', MoveBaseActionResult, statusCallback)
    subWaypoint = rospy.Subscriber('/goal_waypoint', String, waypointCallback)
    rospy.init_node('PoseConductor', anonymous=True)
    rate = rospy.Rate(1) # 10hz

    while not rospy.is_shutdown():
        if goal_reached and waypoints_list:
            print(f"Current waypoint is {nav.current_waypoint}")
            waypoints_list.remove(waypoints_list[0])
            try:
                print(f"Goal Reached, going to next waypoint: {waypoints_list[0]['name']}")
            except:
                print("Move finished")
            goal_reached = False
        if waypoints_list:
            current_waypoint = waypoints_list[0]
            publishPose(current_waypoint,pub)
        rate.sleep()






if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass