import socket
import os
import time
import threading
import rospy
from std_msgs.msg import String
from queue import Queue


class RequestServer:
    """This class acts as a stand-in for the speech-to-text component, in order to avoid needing to speak queries out loud for testing"""
    def _init_(self, **_):
        # drop any kwargs, only accepted for compatibility

        # set connection parameters from environment variables
        self.host = os.environ.get('REQS_HOST', '0.0.0.0')
        self.port = int(os.environ.get('REQS_PORT', 10000))

        # set up ROS node and publishers
        rospy.init_node('webCall', anonymous=True)
        self.goal_pub = rospy.Publisher(
            '/salmon/goal_waypoint', String, queue_size=10
        )
        self.goal_sub = rospy.Subscriber(
            '/salmon/goal_waypoint', String, self.gwp_callback
        )
        self.sub = rospy.Subscriber('/salmon/finished', String, self.f_callback)
        # set up rotating loc 'queue'
        self.last_desk = None  # not rly using rn, but could be useful?
        self.prev_loc = None  # not entirely necessary, but why not
        self.curr_loc = None
        self.next_loc = None

        # set up server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Request Server listening on {self.host}:{self.port}")

        # set up new thread to handle clients
        # so that it doesn't block the main thread
        server_thread = threading.Thread(target=self.start)
        server_thread.start()

    def gwp_callback(self, data):
        self.next_loc = data.data

    def f_callback(self, data):
        if data.data == "SALMON Move finished":
            # TODO: make sure there aren't any shallow copy errors
            self.prev_loc = self.curr_loc
            self.curr_loc = self.next_loc
            self.next_loc = None
            if self.curr_loc[:4] == "desk":
                self.last_desk = self.curr_loc
        else:
            print("RS-err: Unexpected message from /salmon/finished")


    def handle_client(self, client_socket):
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8').strip()
                if not data:
                    break

                self.guruguru(data) # blocking fn

                client_socket.send("done".encode())
        except Exception as e:
            client_socket.close()
            print(f"RS-err: {e}")
        finally:
            client_socket.close()
            print("RS-log: Client disconnected peacefully.")


    def start(self):
        try:
            while True:
                client_socket, addr = self.server_socket.accept()
                print(f"Connection from {addr}")

                # don't put in a separate thread
                # since we only want one client at a time
                self.handle_client(client_socket)
        except KeyboardInterrupt:
            print("\nServer shutting down.")
        finally:
            self.server_socket.close()


    def guruguru(self, new_pos):
        # save this location, in case not returning to a desk
        start_loc = self.curr_loc

        # go to desired location
        self.goal_pub.publish(new_pos)
        while self.curr_loc != new_pos:
            time.sleep(1)

        if self.curr_loc == "box":
            # TODO: send the forklift msg, make it do the thing
            time.sleep(100)

        # return to original position
        self.goal_pub.publish(start_loc)
        while self.curr_loc != start_loc:
            time.sleep(1)


if __name__ == "__main__":
    RequestServer()