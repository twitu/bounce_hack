import itertools as itr
from collections import deque
from random import sample, randint

import networkx as nx

from scooter_simulation import SimulateScooters


class SimulateTrucks:
    NUMBER = 8
    CAPACITY = 10

    def __init__(self, G, office_nodes, metro_node, scooters):
        self.map = G
        self.offices = office_nodes
        self.turns_without_visit = [1] * SimulateScooters.OFFICE_NUM
        self.idle_prob = [randint(1, 30) / 100 for _ in range(SimulateScooters.OFFICE_NUM)]
        self.office_mapping = {office['osmid']: i for i, office in enumerate(self.offices)}
        self.metro = metro_node
        self.truck_pos = [self.map.node.get(i) for i in sample(self.map.nodes, SimulateTrucks.NUMBER)]
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

    def get_shortest_path(self, src, dst):
        return nx.shortest_path(self.map, src['osmid'], dst['osmid'])

    def score_function(self, scooters, dist):
        """
        Designed to recover truck cost 80% of the time

        Args:
            scooters: Number of scooters the truck can pickup
            dist: Distance truck will travel to pick-up location

        Returns:
            score
        """
        return 10 * scooters - 0.87 * dist - 175

    def get_office_scooters(self, office_scooters, node):
        return office_scooters[self.office_mapping[node['osmid']]]

    def take_office_scooters(self, office_scooters, node, take):
        office_scooters[self.office_mapping[node['osmid']]] -= take

    def brute_path_truck(self, truck_id, office_scooters):
        """
        Try all orders of paths that can be taken, taking the order and the path
        with maximum score.

        Args:
            truck_id - indicating truck concerned
            office_scooters List(int): speculated number of scooters at office locations

        Returns:
            steps: chosen path
            office_scooters: remaining number of scooters at office locations
            best_score: score for the path
        """
        cur_cap = self.truck_cap[truck_id]
        cur_pos = self.truck_pos[truck_id]

        def score_order_path(dist, cap_gained, cur_pos, order):
            if not order or cap_gained + cur_cap == SimulateTrucks.CAPACITY:
                return self.score(cap_gained, dist)
            else:
                dest = order[0]
                path_len = len(self.get_shortest_path(cur_pos, dest))
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
        steps = self.get_shortest_path(cur_pos, best_score[0])
        steps = [self.map.node.get(i) for i in steps[1:]]
        take = min(SimulateTrucks.CAPACITY - cur_cap, self.get_office_scooters(office_scooters, steps[-1]))
        self.take_office_scooters(office_scooters, steps[-1], take)
        return steps, office_scooters, best_score

    def brute_algo(self, scooter_qty):
        """
        Try all orders of trucks for all orders of paths that can be taken,
        taking the best order which has the best cumulative score of all paths.
        Method is called every time a truck completes and objective, resetting objectives
        i.e. destination for all trucks.

        Args:
            scooter_qty: number of scooters at office locations
        """
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = self.get_shortest_path(self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    steps, office_scooters, _ = self.brute_path_truck(truck_id, office_scooters)
                    self.next_steps[truck_id] = deque(steps)

    def aging_score(self, scooter_qty):
        return [(a * b * c, i) for i, (a, b, c) in
                enumerate(zip(scooter_qty, self.turns_without_visit, self.idle_prob))]

    def best_aging_score(self, cur_pos, scooter_qty):
        scores = self.aging_score(scooter_qty)
        scores.sort(reverse=True, key=lambda x: x[0])
        return scores[0]

    def greedy_score(self, cur_pos, scooter_qty):
        dist = [len(self.get_shortest_path(cur_pos, office)) for office in self.offices]
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
        """
        Calculates destination and path for all trucks that have,
        reached destination i.e. their next steps queue is None. Method
        is called every turn.

        Args:
            scooter_qty: number of scooters at office locations
            score_func: choosing among aging, greedy or combined score to
                decide paths to take
        """
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = self.get_shortest_path(self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = score_func(self.truck_pos[truck_id], office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = self.get_shortest_path(self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def greedy_algo(self, scooter_qty):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = self.get_shortest_path(self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = self.best_greedy_score(self.truck_pos[truck_id], office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = self.get_shortest_path(self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def aging_algo(self, scooter_qty):
        office_scooters = list(scooter_qty)
        for truck_id in range(SimulateTrucks.NUMBER):
            if not self.next_steps[truck_id]:
                if self.truck_cap[truck_id] == SimulateTrucks.CAPACITY:
                    steps = self.get_shortest_path(self.truck_pos[truck_id], self.metro)
                    steps = [self.map.node.get(i) for i in steps[1:]]
                    self.next_steps[truck_id] = deque(steps)
                else:
                    score, office_id = self.best_aging_score(office_scooters)
                    take = min(SimulateTrucks.CAPACITY - self.truck_cap[truck_id], office_scooters[office_id])
                    if not take:
                        self.next_steps[truck_id] = None
                    else:
                        office_scooters[office_id] -= take
                        path = self.get_shortest_path(self.truck_pos[truck_id], self.offices[office_id])
                        self.next_steps[truck_id] = deque([self.map.node.get(i) for i in path[1:]])

    def update_truck_pos(self, metro_scooters, office_scooters):
        """
        Checks if a truck has reached its objective. If it is a metro,
        add scooters to metro capacity. If it is a office takes scooters,
        according to capacity. Method is called every turn to update truck
        positions.

        Args:
            metro_scooters: number of scooters at metro
            office_scooters: number of scooters at office locations
        """
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

        # log metrics for each turn
        metrics = []
        if not self.dist_travelled:
            metrics.append(0)
        else:
            metrics.append(self.scooters_picked / (SimulateTrucks.NUMBER * self.dist_travelled))
        return metro_scooters, office_scooters, metrics
