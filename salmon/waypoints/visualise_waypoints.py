from json import load
import graphviz

waypoints_file = (__file__.replace("\\", "/"))[::-1].split("/", 1)[1][::-1] + "/positions.json"

print(f"Creating graph from file {waypoints_file}")

waypoints = {}
with open(waypoints_file,"r") as file:
    waypoints = load(file)

dot = graphviz.Digraph('map')  

for waypoint, data in waypoints.items():
    dot.node(waypoint)
    for neighbour in data["neighbours"]:
        dot.edge(waypoint, neighbour)

dot.render()