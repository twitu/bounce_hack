import matplotlib.pyplot as plt
import numpy as np
import osmnx as ox
from matplotlib import animation
from matplotlib.collections import LineCollection

from scooter_simulation import SimulateScooters
from truck_simulation import SimulateTrucks


class BounceSimulation:
    UNIT = 40
    FRAMES = 150

    def __init__(self, score_func="aging"):
        self.node_values = []
        self.frame = 0
        self.metrics = []
        self.G = ox.graph_from_point((12.985660, 77.645015), distance=2000, network_type='drive')
        metro = self.G.node.get(1563273556)
        offices = [
            self.G.node.get(6536735148),
            self.G.node.get(6536735146),
            self.G.node.get(1132680459),
            self.G.node.get(1132675346),
            self.G.node.get(1339408165),
            self.G.node.get(1328155440),
            self.G.node.get(1500759513),
            self.G.node.get(1485686869),
            self.G.node.get(3885545484),
            self.G.node.get(1808901710),
        ]
        self.fixed_points = list(offices)
        self.fixed_points.append(metro)
        self.plot_trucks = None
        self.plot_scooters = None

        # get north, south, east, west values either from bbox parameter or from the
        # spatial extent of the edges' geometries
        self.edges = ox.graph_to_gdfs(self.G, nodes=False, fill_edge_geometry=True)
        west, south, east, north = self.edges.total_bounds

        # if caller did not pass in a fig_width, calculate it proportionately from
        # the fig_height and bounding box aspect ratio
        bbox_aspect_ratio = (north - south) / (east - west)
        fig_height = 12  # in inches
        fig_width = fig_height / bbox_aspect_ratio

        # create simulation object
        self.scooters = SimulateScooters(self.G, offices, metro)
        self.trucks = SimulateTrucks(self.G, offices, metro, self.scooters)
        if score_func == "aging":
            self.score_func = self.trucks.best_aging_score
        elif score_func == "greedy":
            self.score_func = self.trucks.best_greedy_score
        else:
            self.score_func = self.trucks.best_combined_score

        # create the figure and axis
        self.fig, self.ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='w')

        # intialize animation function with setup plot, attach update plot function for each frame
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, frames=BounceSimulation.FRAMES,
                                           init_func=self.setup_plot, blit=False)

    def setup_plot(self):
        # draw the edges as lines from node to node
        lines = []
        for u, v, data in self.G.edges(keys=False, data=True):
            # if it doesn't have a geometry attribute, the edge is a straight
            # line from node to node
            x1 = self.G.nodes[u]['x']
            y1 = self.G.nodes[u]['y']
            x2 = self.G.nodes[v]['x']
            y2 = self.G.nodes[v]['y']
            line = [(x1, y1), (x2, y2)]
            lines.append(line)

        # add the lines to the axis as a linecollection
        lc = LineCollection(lines, colors='#999999', linewidths=1, alpha=1, zorder=2)

        # set the extent of the figure
        west, south, east, north = self.edges.total_bounds
        margin = 0.02
        margin_ns = (north - south) * margin
        margin_ew = (east - west) * margin
        self.ax.set_ylim((south - margin_ns, north + margin_ns))
        self.ax.set_xlim((west - margin_ew, east + margin_ew))

        # configure axis appearance
        xaxis = self.ax.get_xaxis()
        yaxis = self.ax.get_yaxis()

        xaxis.get_major_formatter().set_useOffset(False)
        yaxis.get_major_formatter().set_useOffset(False)

        # set title
        self.ax.set_title("Frame 0")

        # display fixed points
        for point in self.fixed_points[:-1]:
            self.ax.plot(point['x'], point['y'], 'o', color='blue')
        red_fixed = self.fixed_points[-1]
        self.ax.plot(red_fixed['x'], red_fixed['y'], 'o', color='red')

        # setup scooter scatter artist
        nodeXs, nodeYs = self.scooters.node_positions()
        node_size = self.scooters.node_size()
        nodeXs = np.array(nodeXs)
        nodeYs = np.array(nodeYs)
        self.plot_scooters = self.ax.scatter(nodeXs, nodeYs, s=node_size, c=node_size, alpha=0.6, edgecolor=None,
                                             zorder=10,
                                             cmap='gnuplot')

        # setup truck scatter artist
        truckx, trucky = self.trucks.get_pos()
        truckx, trucky = np.array(truckx), np.array(trucky)
        truck_size = self.trucks.get_size()
        self.plot_trucks = self.ax.scatter(truckx, trucky, s=truck_size, c=truck_size, alpha=0.6, edgecolor=None,
                                           zorder=15, cmap='plasma')

        # if the graph is not projected, conform the aspect ratio to not stretch the plot
        coslat = np.cos((min(nodeYs) + max(nodeYs)) / 2. / 180. * np.pi)
        self.ax.set_aspect(1. / coslat)
        self.fig.canvas.draw()

    def update_plot(self, i):
        # stop simulation to prevent negative overflow
        if i == BounceSimulation.FRAMES - 1:
            quit()
        self.ax.set_title("Turn {}".format(i))

        # modify scooter scatter plot artist
        self.metrics.append(self.scooters.turn(i))
        node_size = np.array(self.scooters.node_size())
        x, y = self.scooters.node_positions()
        node_pos = np.c_[x, y]
        self.plot_scooters.set_sizes(node_size)  # changes size of points
        self.plot_scooters.set_array(node_size)  # changes color of points
        self.plot_scooters.set_offsets(node_pos)  # changes position of points

        # modify truck scatter plot artist
        self.trucks.calculate_path(self.scooters.scooters_office, self.score_func)
        metro, office, metric = self.trucks.update_truck_pos(self.scooters.scooters_metro,
                                                             self.scooters.scooters_office)
        self.metrics.append(metric)
        self.scooters.scooters_metro = metro
        self.scooters.scooters_office = office
        truckx, trucky = self.trucks.get_pos()
        truck_pos = np.c_[truckx, trucky]
        truck_size = np.array(self.trucks.get_size())
        self.plot_trucks.set_sizes(truck_size)
        self.plot_trucks.set_array(truck_size)
        self.plot_trucks.set_offsets(truck_pos)
