#!/usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion
from move_base_msgs.msg import MoveBaseActionResult
from std_msgs.msg import Header
import json
import os

waypoints_dir = os.path.abspath("src/magni_robot/salmon/waypoints/positions.json")
goal_reached = False

def statusCallback(data):
    status = data.status.status
    global goal_reached
    if status==3:
        goal_reached = True
    else:
        goal_reached = False

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
    index = 0
    pub = rospy.Publisher('/move_base_simple/goal', PoseStamped, queue_size=10)
    sub = rospy.Subscriber('/move_base/result', MoveBaseActionResult, statusCallback)
    rospy.init_node('PoseConductor', anonymous=True)
    rate = rospy.Rate(1) # 10hz
    with open(waypoints_dir,"r") as f:
        waypoints = json.load(f)
        waypoints = list(waypoints.values())

    while not rospy.is_shutdown():
        if goal_reached:
            print(f"Goal Reached, going to waypoint {index}")
            index = (index+1)%len(waypoints)
            goal_reached = False
        current_waypoint = waypoints[index]
        publishPose(current_waypoint,pub)
        rate.sleep()






if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass