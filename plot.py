import itertools as itr
import random
import sys
from collections import deque

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import osmnx as ox
from matplotlib import animation
from matplotlib.collections import LineCollection


def get_shortest_path(map, src, dst):
    return nx.shortest_path(map, src['osmid'], dst['osmid'])


class SimulateTrucks:
    NUMBER = 8
    CAPACITY = 10

    def __init__(self, G, office_nodes, metro_node, scooters):
        self.map = G
        self.offices = office_nodes
        self.turns_without_visit = [1] * SimulateScooters.OFFICE_NUM
        self.idle_prob = [random.randint(1, 30) / 100 for _ in range(SimulateScooters.OFFICE_NUM)]
        self.office_mapping = {office['osmid']: i for i, office in enumerate(self.offices)}
        self.metro = metro_node
        self.truck_pos = [self.map.node.get(i) for i in random.sample(self.map.nodes, SimulateTrucks.NUMBER)]
        self.truck_cap = [0] * SimulateTrucks.NUMBER
        self.scooters_sim = scooters
        self.next_steps = [None] * SimulateTrucks.NUMBER
        self.scooters_picked = 0
        self.dist_travelled = 0

    def get_pos(self):
        x = [pos['x'] for pos in self.truck_pos]
        y = [pos['y'] for pos in self.truck_pos]
        return x, y

    def get_size(self):
        return [(self.scooters_sim.scooter_unit + cap * cap) for cap in self.truck_cap]

    def score_function(self, scooters, dist):
        return 10 * scooters - 0.87 * dist - 175

    def get_office_scooters(self, office_scooters, node):
        return office_scooters[self.office_mapping[node['osmid']]]

    def take_office_scooters(self, office_scooters, node, take):
        office_scooters[self.office_mapping[node['osmid']]] -= take

    def simplex_path_truck(self, truck_id, office_scooters):
        cur_cap = self.truck_cap[truck_id]
        cur_pos = self.truck_pos[truck_id]

        def score_order_path(dist, cap_gained, cur_pos, order):
            if not order or cap_gained + cur_cap == SimulateTrucks.CAPACITY:
                return self.score(cap_gained, dist)
            else:
                dest = order[0]
                path_len = len(get_shortest_path(self.map, cur_pos, dest))
                cap_gained += min(SimulateTrucks.CAPACITY - cur_cap, self.get_office_scooters(office_scooters, dest))
                self.take_office_scooters(office_scooters, dest, cap_gained)
                score1 = score_order_path(dist + path_len, cap_gained, dest, order[1:])
                path_len += len(nx.shortest_path(self.map, dest['osmid'], self.metro['osmid']))
                score2 = self.score(cap_gained, path_len)
                return max(score1, score2)

        paths = [(score_order_path(0, 0, cur_pos, order), order) for order in
                 itr.permutations(self.offices, len(self.offices)) if order[0] is not cur_pos]
        paths.sort(key=lambda x: x[0], reverse=True)
        best_score = paths[0][0]
        steps = get_shortest_path(self.map, cur_pos, best_score[0])
        steps = [self.map.node.get(i) for i in steps[1:]]
        take = min(SimulateTrucks.CAPACITY - cur_cap, self.get_office_scooters(office_scooters, steps[-1]))
        self.take_office_scooters(office_scooters, steps[-1], take)
        return steps, office_scooters, best_score

    def simplex_algo(self, scooter_qty):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = get_shortest_path(self.map, self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    steps, office_scooters, _ = self.simplex_path_truck(truck_id, office_scooters)
                    self.next_steps[truck_id] = deque(steps)

    def aging_score(self, scooter_qty):
        return [(a * b * c, i) for i, (a, b, c) in
                enumerate(zip(scooter_qty, self.turns_without_visit, self.idle_prob))]

    def best_aging_score(self, cur_pos, scooter_qty):
        scores = self.aging_score(scooter_qty)
        scores.sort(reverse=True, key=lambda x: x[0])
        return scores[0]

    def greedy_score(self, cur_pos, scooter_qty):
        dist = [len(get_shortest_path(self.map, cur_pos, office)) for office in self.offices]
        scooters = [min(SimulateTrucks.CAPACITY - self.truck_cap[i], scooter_qty[i]) for i in
                    range(SimulateTrucks.NUMBER)]
        return [(self.score_function(a, b), i) for i, (a, b) in enumerate(zip(scooters, dist))]

    def best_greedy_score(self, cur_pos, scooter_qty):
        score = self.greedy_score(cur_pos, scooter_qty)
        score.sort(reverse=True, key=lambda x: x[0])
        return score[0]

    def combined_score(self, cur_pos, scooter_qty, a=0.7):
        aging = self.aging_score(scooter_qty)
        greedy = self.greedy_score(cur_pos, scooter_qty)
        combined = [(age_score * a + greedy_score * (1 - a), i) for i, ((age_score, _), (greedy_score, _)) in
                    enumerate(zip(aging, greedy))]
        return combined

    def best_combined_score(self, cur_pos, scooter_qty):
        combined = self.combined_score(cur_pos, scooter_qty)
        combined.sort(reverse=True, key=lambda x: x[0])
        return combined[0]

    def calculate_path(self, scooter_qty, score_func):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = get_shortest_path(self.map, self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = score_func(self.truck_pos[truck_id], office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = get_shortest_path(self.map, self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def greedy_algo(self, scooter_qty):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = get_shortest_path(self.map, self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = self.best_greedy_score(self.truck_pos[truck_id], office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = get_shortest_path(self.map, self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def aging_algo(self, scooter_qty):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = get_shortest_path(self.map, self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = self.best_aging_score(office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = get_shortest_path(self.map, self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def update_truck_pos(self, metro_scooters, office_scooters):
        for i, steps in enumerate(self.next_steps):
            if not steps:
                continue
            step = steps.popleft()
            self.dist_travelled += 1
            if step == self.metro:
                # delivered scooters to metro
                metro_scooters += self.truck_cap[i]
                self.truck_cap[i] = 0
                self.truck_pos[i] = step
                self.next_steps[i] = None
            elif step in self.offices:
                # reached office location
                office_id = self.office_mapping[step['osmid']]
                take = min(SimulateTrucks.CAPACITY - self.truck_cap[i], office_scooters[office_id])
                office_scooters[office_id] -= take
                self.truck_cap[i] += take
                self.turns_without_visit[office_id] = 0
                self.scooters_picked += take
                self.truck_pos[i] = step
                self.next_steps[i] = None
            else:
                # take next step
                self.truck_pos[i] = step

        self.turns_without_visit = [i + 1 for i in self.turns_without_visit]
        if not self.dist_travelled:
            print(0)
        else:
            print(self.scooters_picked / (SimulateTrucks.NUMBER * self.dist_travelled))
        return metro_scooters, office_scooters


class SimulateScooters:
    IN_RATE = 30  # customers exiting metro per turn
    OUT_RATE = 2  # customers exiting office per turn
    OFFICE_NUM = 10  # number of offices
    OFFICE_PROB = 1 / OFFICE_NUM  # equal probability of going to any office
    WAITING_TIME = 3  # maximum turns customer will wait for scooter
    SCOOTERS_TOTAL = 200  # scooters in simulation
    REPLENISH = 0  # scooters come back to metro

    def __init__(self, G, office_nodes, metro_node, with_trucks):
        """
        Initialize scooters, offices and metro positions for simulation

        Args:
            G <graph object>: map of city
            office_nodes List[nodes]
            metro_node node
        """
        self.map = G
        self.que = deque()  # que of waiting customers
        self.customers_served = 0
        self.customers_dropped = 0
        self.total_waiting_time = 0
        self.scooters = [metro_node] * SimulateScooters.SCOOTERS_TOTAL  # scooters moving to destination
        self.scooters_ride = [None] * SimulateScooters.SCOOTERS_TOTAL  # scooter destination
        self.offices = office_nodes  # office location with parked scooters
        self.metro = metro_node  # metro location with parked scooters
        self.scooters_metro = SimulateScooters.SCOOTERS_TOTAL
        self.scooters_office = [0] * SimulateScooters.OFFICE_NUM
        self.office_paths = [deque(nx.shortest_path(self.map, self.metro['osmid'], office['osmid'])) for office in
                             self.offices]
        self.scooter_unit = 15
        self.fixed_point = 40
        self.under_utilization = 0
        if not with_trucks:
            SimulateScooters.REPLENISH = 0.01

    def node_positions(self):
        x = [self.metro['x']] + [office['x'] for office in self.offices] + [scooter['x'] for scooter in self.scooters]
        y = [self.metro['y']] + [office['y'] for office in self.offices] + [scooter['y'] for scooter in self.scooters]
        return x, y

    def node_size(self):
        scooters = []
        for ride in self.scooters_ride:
            if ride:
                scooters.append(self.scooter_unit)
            else:
                scooters.append(0)
        mapped_scooters_office = [n * n + self.fixed_point for n in self.scooters_office]
        return [self.scooters_metro * self.scooters_metro + self.fixed_point] + mapped_scooters_office + scooters

    def turn(self, turn):
        """
        Make changes required for a turn

        Args:
            turn int: current turn number
        """
        # small probability to replenish scooters
        for i, pos in enumerate(self.scooters):
            for j, office in enumerate(self.offices):
                if pos == office and random.random() < SimulateScooters.REPLENISH:
                    self.scooters_office[j] -= 1
                    self.scooters[i] = self.metro
                    self.scooters_ride[i] = None
                    self.scooters_metro += 1

        # update currently ridden scooters
        for i, ride in enumerate(self.scooters_ride):
            if not ride:
                continue
            next_pos = ride.popleft()
            if not ride:
                # ride completed at office location
                for j, office in enumerate(self.offices):
                    if office['osmid'] == next_pos:
                        self.scooters_office[j] += 1
                        self.scooters_ride[j] = None

            self.scooters[i] = self.map.node.get(next_pos)

        while self.que:
            if self.que[0] == turn:
                # remove waiting customers
                self.que.popleft()
                self.customers_dropped += 1
            else:
                if self.scooters_metro:
                    # schedule new scooters and 
                    office_id = random.randint(0, SimulateScooters.OFFICE_NUM - 1)
                    for j, ride in enumerate(self.scooters_ride):
                        if not ride:
                            self.scooters_ride[j] = deque(self.office_paths[office_id])
                            self.scooters_ride[j].popleft()
                            break
                    drop_turn = self.que.popleft()
                    self.scooters_metro -= 1
                    self.customers_served += 1
                    self.total_waiting_time += SimulateScooters.WAITING_TIME + turn - drop_turn
                else:
                    break

        # add new customers
        for i in range(SimulateScooters.IN_RATE):
            self.que.append(turn + SimulateScooters.WAITING_TIME)

        # add underutilization to scooters that are not moving
        for ride in self.scooters_ride:
            if not ride:
                self.under_utilization += 1

        # log
        if not self.customers_served:
            print(0)
        else:
            print(self.total_waiting_time / self.customers_served)
        print(self.customers_dropped)
        if not turn:
            print(0)
        else:
            print(self.under_utilization / (SimulateScooters.SCOOTERS_TOTAL * turn))


class BounceSimulation:
    UNIT = 40
    FRAMES = 150

    def __init__(self, with_trucks=True, score_func="aging"):
        self.node_values = []
        self.frame = 0
        self.plot_nodes = None
        # self.G = ox.graph_from_point((37.79, -122.41), distance=750, network_type='drive')
        # metro = self.G.node.get(65362171)
        # offices = [
        #     self.G.node.get(552853360),
        #     self.G.node.get(1580501206),
        #     self.G.node.get(65334128),
        #     self.G.node.get(65307363),
        # ]
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
        self.plot_lines = None
        self.with_trucks = True
        self.plot_trucks = None

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
        self.scooters = SimulateScooters(self.G, offices, metro, with_trucks)
        if with_trucks:
            self.trucks = SimulateTrucks(self.G, offices, metro, self.scooters)
            if score_func == "aging":
                self.score_func = self.trucks.best_aging_score
            elif score_func == "greedy":
                self.score_func = self.trucks.best_greedy_score
            else:
                self.score_func = self.trucks.best_combined_score

        # create the figure and axis
        self.fig, self.ax = plt.subplots(figsize=(fig_width, fig_height), facecolor='w')

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
        self.plot_lines = self.ax.add_collection(lc)

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

        # compute node sizes
        nodeXs, nodeYs = self.scooters.node_positions()
        node_size = self.scooters.node_size()
        nodeXs = np.array(nodeXs)
        nodeYs = np.array(nodeYs)
        self.plot_nodes = self.ax.scatter(nodeXs, nodeYs, s=node_size, c=node_size, alpha=0.6, edgecolor=None,
                                          zorder=10,
                                          cmap='gnuplot')
        if self.with_trucks:
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
        self.scooters.turn(i)
        node_size = np.array(self.scooters.node_size())
        self.plot_nodes.set_sizes(node_size)
        self.plot_nodes.set_array(node_size)
        x, y = self.scooters.node_positions()
        node_pos = np.c_[x, y]
        self.plot_nodes.set_offsets(node_pos)
        if self.with_trucks:
            self.trucks.calculate_path(self.scooters.scooters_office, self.score_func)
            metro, office = self.trucks.update_truck_pos(self.scooters.scooters_metro, self.scooters.scooters_office)
            self.scooters.scooters_metro = metro
            self.scooters.scooters_office = office
            truckx, trucky = self.trucks.get_pos()
            truck_pos = np.c_[truckx, trucky]
            truck_size = np.array(self.trucks.get_size())
            self.plot_trucks.set_sizes(truck_size)
            self.plot_trucks.set_array(truck_size)
            self.plot_trucks.set_offsets(truck_pos)


if __name__ == "__main__":
    simulation = BounceSimulation(with_trucks=True, score_func=sys.argv[1])
    random.seed(25)
    plt.show()
