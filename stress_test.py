import time
import numpy as np
import os
import signal


# CONSTANTS
NUM_SEEDS = 6
KILLS_ROUND = 3
JOINS_ROUND = 3
NUM_ROUNDS = 3
COOLDOWN = 10
GRACE_PERIOD = 10


class Simulation:
    def __init__(self):
        self.ports = set()
        self.peer_to_pid = dict()

    def generate_peers(self, cnt_peers):
        # generate 2 * cnt_peers distinct numbers, that are also not in self.peers
        ports = set()
        while len(ports) < 2 * cnt_peers:
            rand_port = np.random.randint(2000, 60000+1)
            if rand_port in self.ports:
                continue
            ports.add(rand_port)

        peers, ports = [], list(ports)
        for i in range(0, len(ports), 2):
            peers.append((ports[i], ports[i + 1]))
        return peers

    def start_seed(self, seed, peers):
        type = 'node' if np.random.rand() < 0.5 else 'lazy_node'
        print(f'Forking seed <{type}> {seed}')
        pid = os.fork()
        if pid > 0:
            self.ports.add(seed[0])
            self.ports.add(seed[1])
            self.peer_to_pid[seed] = pid
        elif pid == 0:
            args = [f"./build/{type}", "--ports", str(seed[0]), str(seed[1])]
            for peer in peers:
                args.append("--seed")
                args.append(str(peer[0]))
                args.append(str(peer[1]))
            os.execv(f"./build/{type}", args)
        else:
            print("Error forking the process")

    def join_peer(self, peer, gateway):
        type = 'node' if np.random.rand() < 0.5 else 'lazy_node'
        print(f'Forking peer <{type}> {peer} to join {gateway}')
        pid = os.fork()
        if pid > 0:
            self.ports.add(peer[0])
            self.ports.add(peer[1])
            self.peer_to_pid[peer] = pid
        elif pid == 0:
            args = [f"./build/{type}", "--ports", str(peer[0]), str(peer[1])]
            args.extend(["--join", str(gateway[0]), str(gateway[1])])
            os.execv(f"./build/{type}", args)
        else:
            print("Error forking the process")

    def kill_peer(self, peer):
        print(f'Killing peer {peer}')
        os.kill(self.peer_to_pid[peer], signal.SIGINT)
        self.ports.remove(peer[0])
        self.ports.remove(peer[1])
        del self.peer_to_pid[peer]

    def get_peers(self):
        return self.peer_to_pid.keys()


def main():
    simulation = Simulation()

    # generate seeds + fork seeds
    seeds = simulation.generate_peers(NUM_SEEDS)
    for i in range(len(seeds)):
        simulation.start_seed(seeds[i], seeds[:i] + seeds[i+1:])

    for round in range(NUM_ROUNDS):
        time.sleep(COOLDOWN)

        # kill peers
        peers = list(simulation.get_peers())
        idx_peers_to_kill = np.random.choice(len(peers), KILLS_ROUND, replace=False)
        for idx in idx_peers_to_kill:
            simulation.kill_peer(peers[idx])

        # join new peers
        peers = list(simulation.get_peers())
        gateways_idx = np.random.choice(len(peers), JOINS_ROUND, replace=False)
        new_peers = simulation.generate_peers(JOINS_ROUND)
        for i in range(len(new_peers)):
            simulation.join_peer(new_peers[i], peers[gateways_idx[i]])

        # print expected network configuration
        peers = list(simulation.get_peers())
        print(f'Expected network configuration {len(peers)} peers: {peers}')

    time.sleep(GRACE_PERIOD)
    peers = list(simulation.get_peers())
    for peer in peers:
        simulation.kill_peer(peer)


if __name__ == "__main__":
    main()
