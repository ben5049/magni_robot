from json import load
import graphviz

waypoints_file = "positions.json"

waypoints = {}
with open(waypoints_file,"r") as file:
    waypoints = load(file)

dot = graphviz.Digraph('map')  

for waypoint, data in waypoints.items():
    dot.node(waypoint)
    for neighbour in data["neighbours"]:
        dot.edge(waypoint, neighbour)

dot.render()