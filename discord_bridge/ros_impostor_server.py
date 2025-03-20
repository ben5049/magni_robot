import socket
from socket import timeout
import os
import time
import threading
import rospy
from std_msgs.msg import String
from queue import Queue


class RequestServer:
    """This class acts as a stand-in for the speech-to-text component, in order to avoid needing to speak queries out loud for testing"""
    def __init__(self, **_):
        # drop any kwargs, only accepted for compatibility

        # set connection parameters from environment variables
        self.host = os.environ.get('REQS_HOST', '0.0.0.0')
        self.port = int(os.environ.get('REQS_PORT', 10000))

        ##Status flag for if forklift can be sent
        self.forklift_ready = False

        # set up ROS node and publishers
        rospy.init_node('webCall', anonymous=True)
        self.goal_pub = rospy.Publisher(
            '/salmon/goal_waypoint', String, queue_size=10
        )
        self.goal_sub = rospy.Subscriber(
            '/salmon/goal_waypoint', String, self.gwp_callback
        )
        self.sub = rospy.Subscriber(
            '/salmon/finished', String, self.fin_callback
        )
        # set up rotating loc 'queue'
        self.last_desk = None  # not rly using rn, but could be useful?
        self.prev_loc = None  # not entirely necessary, but why not
        self.curr_loc = None
        self.next_loc = None

        # abstract into fn call for restarting
        self.start_server()

    def gwp_callback(self, data):
        """goal waypoint callback"""
        print(data.data)
        self.next_loc = data.data
        print("Received Info!")
        print(self.next_loc)

    def fin_callback(self, data):
        """salmon finished callback"""
        if data.data == "SALMON Move finished":
            # TODO: make sure there aren't any shallow copy errors
            self.prev_loc = self.curr_loc
            self.curr_loc = self.next_loc
            self.next_loc = None
            if self.curr_loc[:4] == "desk":
                self.last_desk = self.curr_loc
            if self.curr_loc == "box":
                self.forklift_ready=True
                print("forklift ready to move")
            print("SALMON Finished!")
            print({self.prev_loc, self.curr_loc, self.next_loc})
        else:
            print(
                f"RIS-err: Unexpected msg from /salmon/finished: {data.data}"
            )


    def start_server(self):
        # reset port to account for server restarts
        self.port = int(os.environ.get('REQS_PORT', 10000))

        # configure server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setblocking(1)
        # self.server_socket.settimeout(None)

        # keep attempting to restart server until it works
        # am assuming human intervention if error persists
        while True:
            try:
                self.server_socket.bind((self.host, self.port))
                break
            except socket.error as e:
                # usually occurs due to "Address already in use" errors
                print(f"RIS-err: socket error: {e}")
                self.port += 1
            except Exception as e:
                print(f"RIS-err: encountered exception: {e}")

        self.server_socket.listen(5)
        print(f"Request Server started on {self.host}:{self.port}")

        handler_thread = threading.Thread(target=self.start)
        handler_thread.start()


    def start(self):
        try:
            # to allow server to handle client disconnects and reconnects
            while True:
                client_socket, addr = self.server_socket.accept(timeout=None)
                client_socket.setblocking(1)
                print(f"Connection from {addr}")

                # don't put in a separate thread: only want one client at a time
                self.handle_client(client_socket)
        except timeout:  # TODO: is it this or TimeoutError?
            # if server timed out, restart server thread
            self.server_socket.close()
            self.start_server()
            return  # to skip `finally` section
        except KeyboardInterrupt:
            print("\nServer shutting down.")
        except Exception as e:
            print(f"RIS-err: {e}")
        finally:
            self.server_socket.close()


    def handle_client(self, client_socket):
        """
        This logic sequence defines the bot's movement behaviour,\\
        due to its interaction with the user.\n
        In order to modify the bot's movement behaviours,\\
        this function must be updated to handle more event cases.
        """
        while True:
            try:
                data = client_socket.recv(4096).decode('utf-8').strip()
                print(f"RIS-log: received msg1 from client: {data}")

                if not data:
                    continue  # start listening again

                # send bot to desired location
                start_loc = self.guruguru(data)  # blocking fn

                client_socket.sendall("arrived".encode())

                if start_loc is None:
                    raise ValueError(
                        f"RIS-err: no starting location, debug this please"
                    )

                # forklift should take longer than this
                time.sleep(50)  # TODO: tune this correctly

                # for now, this is only implemented for box fetches
                data = client_socket.recv(4096).decode('utf-8').strip()
                print(f"RIS-log: received msg2 from client: {data}")

                if not data:
                    continue
                elif data != "FComplete":
                    # if the client has sent something other than
                    # a notification that the forklift is done, restart action
                    continue

                # send bot back to starting position
                self.kaerukaeru(start_loc)  # blocking fn

                # client will be waiting for return message
                client_socket.sendall("returned".encode())
            except Exception as e:
                # peacefully close socket before re-raising error for parent
                client_socket.close()
                raise e
            finally:
                client_socket.close()
                print("RIS-log: Client disconnected peacefully.")


    def guruguru(self, destination):
        """go to desired location"""
        print(f"RIS-log: guruguru o hajimemasu, {destination} e")

        # save this location, in case not returning to a desk
        start_loc = self.curr_loc

        print(f"""RIS-log: loc queue: {
            self.prev_loc, self.curr_loc, self.next_loc
        }""")

        # go to desired location
        self.goal_pub.publish(destination)
        while self.curr_loc != destination:
            time.sleep(1)

        # large match statement could be implemented to handle other cases
        if self.curr_loc == "box":
            # since only implementing forklift here
            # have hard-coded this behaviour into `handle_client`
            return start_loc

        return None


    def kaerukaeru(self, start_pos):
        """return from desired location to starting location"""
        print(f"RIS-log: kaerukaeru o hajimemasu, {start_pos} e")

        print(f"""RIS-log: loc queue: {
            self.prev_loc, self.curr_loc, self.next_loc
        }""")

        # go to desired location
        self.goal_pub.publish(start_pos)
        while self.curr_loc != start_pos:
            time.sleep(1)

        return "yay ^-^"


if __name__ == "__main__":
    RequestServer()


# TODO: keep this out of git, but revisit tmr
previous_gg_implementation = """
# go to desired location
if new_pos!="FComplete":
    self.goal_pub.publish(new_pos)
elif new_pos=="dummy":
    pass
else:
    print("Previous desk was:")
    print(self.prev_loc)
    print("Going there now...")
    self.goal_pub.publish(self.prev_loc)

while self.curr_loc != new_pos:
    time.sleep(1)

if self.forklift_ready:
    # TODO: send the forklift msg, make it do the thing
    print("doing forklift things")
    self.forklift_ready = False"
"""