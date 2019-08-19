from collections import deque
from random import randint, random

import networkx as nx


class SimulateScooters:
    IN_RATE = 30  # customers exiting metro per turn
    OFFICE_NUM = 10  # number of offices
    OFFICE_PROB = 1 / OFFICE_NUM  # equal probability of going to any office
    WAITING_TIME = 3  # maximum turns customer will wait for scooter
    SCOOTERS_TOTAL = 200  # scooters in simulation
    REPLENISH = 0.005  # scooters come back to metro due random commute
    SIZE = 15  # size of scooter on graph

    def __init__(self, G, office_nodes, metro_node):
        """
        Initialize scooters, offices and metro positions for simulation

        Args:
            G <graph object>: map of city
            office_nodes List[nodes]: List of office node positions
            metro_node node: metro node position
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
        self.fixed_point = 40
        self.under_utilization = 0

    def node_positions(self):
        """
        Make two separate list of positions for all points of interest

        Return:
            (List(int), List(int)) - List of x and y coordinates
        """
        x = [self.metro['x']] + [office['x'] for office in self.offices] + [scooter['x'] for scooter in self.scooters]
        y = [self.metro['y']] + [office['y'] for office in self.offices] + [scooter['y'] for scooter in self.scooters]
        return x, y

    def node_size(self):
        """
        Make array of number of scooters parked at metro and offices. All scooters being ridden
        have display a single fixed size point.

        Return:
            List(int): indicating size of point
        """
        scooters = []
        for ride in self.scooters_ride:
            if ride:
                scooters.append(SimulateScooters.SIZE)
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
                if pos == office and random() < SimulateScooters.REPLENISH:
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

        # handle customers waiting at metro
        while self.que:
            if self.que[0] == turn:
                # remove waiting customers
                self.que.popleft()
                self.customers_dropped += 1
            else:
                if self.scooters_metro:
                    # schedule new scooters and
                    office_id = randint(0, SimulateScooters.OFFICE_NUM - 1)
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

        # add under utilization to scooters that are not moving
        for ride in self.scooters_ride:
            if not ride:
                self.under_utilization += 1

        # log metrics for each turn
        metrics = []
        if not self.customers_served:
            metrics.append(0)
        else:
            metrics.append(self.total_waiting_time / self.customers_served)
        metrics.append(self.customers_dropped)
        if not turn:
            metrics.append(0)
        else:
            metrics.append(self.under_utilization / (SimulateScooters.SCOOTERS_TOTAL * turn))

        return metrics
