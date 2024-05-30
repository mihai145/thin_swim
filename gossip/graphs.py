from abc import ABC, abstractmethod
import numpy as np
import networkx as nx


class Graph(ABC):
    @abstractmethod
    def get_random_neighbor(self, idx):
        pass

    @abstractmethod
    def reset(self):
        pass


class CompleteGraph(Graph):
    def __init__(self, n, fixed_scheduling=True):
        self.n = n
        self.picks = np.random.randint(0, self.n, size=n * int(np.log2(n)) * 5)
        self.ptr = -1
        self.fixed_scheduling = fixed_scheduling

    def get_random_neighbor(self, idx):
        if self.fixed_scheduling:
            self.ptr += 1
            return self.picks[self.ptr]

        return np.random.randint(0, self.n)

    def get_neighbors(self, idx):
        return [x for x in range(self.n) if x != idx]

    def reset(self):
        if self.fixed_scheduling:
            self.ptr = -1


class RingGraph(Graph):
    def __init__(self, n, fixed_scheduling=True):
        self.n = n

    def get_random_neighbor(self, idx):
        r = np.random.randint(3)
        if r == -1:
            return (idx - 1 + self.n) % self.n
        if r == 0:
            return idx
        return (idx + 1) % self.n

    def reset(self):
        pass


class RandomGeometricGraph(Graph):
    def __init__(self, n, rad, fixed_scheduling=True):
        self.n = n
        self.rad = rad

        # construct graph (making sure it is connected)
        while True:
            K = nx.random_geometric_graph(n, radius=rad, dim=3)
            if nx.is_connected(K):
                self.rad = rad
                break

        self.neighbors = dict()
        for edge in K.edges():
            if edge[0] not in self.neighbors:
                self.neighbors[edge[0]] = [edge[1]]
            else:
                self.neighbors[edge[0]].append(edge[1])

            if edge[1] not in self.neighbors:
                self.neighbors[edge[1]] = [edge[0]]
            else:
                self.neighbors[edge[1]].append(edge[0])

        self.fixed_scheduling = fixed_scheduling
        if fixed_scheduling:
            # choose scheduling if fixed
            self.picks = dict()
            for node in range(self.n):
                self.picks[node] = []
                for _ in range(int(np.log2(self.n) * 1 / self.rad) * 5):
                    idx = np.random.randint(0, len(self.neighbors[node]) + 1)
                    if idx < len(self.neighbors[node]):
                        self.picks[node].append(self.neighbors[node][idx])
                    else:
                        self.picks[node].append(node)

            # init ptrs
            self.ptr = {x: -1 for x in range(self.n)}

    def get_random_neighbor(self, idx):
        if self.fixed_scheduling:
            self.ptr[idx] += 1
            return self.picks[idx][self.ptr[idx]]
        else:
            rand_idx = np.random.randint(0, len(self.neighbors[idx]) + 1)
            if rand_idx < len(self.neighbors[idx]):
                return self.neighbors[idx][rand_idx]
            else:
                return idx

    def get_neighbors(self, idx):
        return self.neighbors[idx]

    def reset(self):
        if self.fixed_scheduling:
            self.ptr = {x: -1 for x in range(self.n)}
