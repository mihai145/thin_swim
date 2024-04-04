import time
import numpy as np
import os
import signal


# CONSTANTS
NUM_SEEDS = 20
KILLS_ROUND = 6
JOINS_ROUND = 6
NUM_ROUNDS = 10
COOLDOWN = 8
GRACE_PERIOD = 5


# UTILS
def parse_ts(ts):
    splits = ts.split(':')
    return int(splits[0]) * 1000000000 + int(splits[1])

def parse_peer(peer):
    splits = peer.split('-')
    return (int(splits[0]), int(splits[1][:-1]) if splits[1][-1]==',' else int(splits[1]))


class Simulation:
    def __init__(self):
        self.ports = set()
        self.peer_to_pid = dict()
        self.history = set()
        self.history_peers = set()
        self.rounds = []

    def generate_peers(self, cnt_peers):
        # generate 2 * cnt_peers distinct numbers, that are also not in self.peers
        ports = set()
        while len(ports) < 2 * cnt_peers:
            rand_port = np.random.randint(2000, 60000+1)
            if rand_port in self.ports or rand_port in self.history:
                continue
            ports.add(rand_port)

        peers, ports = [], list(ports)
        for i in range(0, len(ports), 2):
            peers.append((ports[i], ports[i + 1]))
        return peers

    def start_seed(self, seed, peers):
        print(f'Forking seed {seed}')
        self.history_peers.add(seed)

        pid = os.fork()
        if pid > 0:
            self.ports.add(seed[0])
            self.ports.add(seed[1])
            self.history.add(seed[0])
            self.history.add(seed[1])
            self.peer_to_pid[seed] = pid
        elif pid == 0:
            args = [f"./build/node", "--ports", str(seed[0]), str(seed[1])]
            for peer in peers:
                args.append("--seed")
                args.append(str(peer[0]))
                args.append(str(peer[1]))
            os.execv(f"./build/node", args)
        else:
            print("Error forking the process")

    def join_peer(self, peer, gateway):
        print(f'Forking peer {peer} to join {gateway}')
        self.history_peers.add(peer)

        pid = os.fork()
        if pid > 0:
            self.ports.add(peer[0])
            self.ports.add(peer[1])
            self.history.add(peer[0])
            self.history.add(peer[1])
            self.peer_to_pid[peer] = pid
        elif pid == 0:
            args = [f"./build/node", "--ports", str(peer[0]), str(peer[1])]
            args.extend(["--join", str(gateway[0]), str(gateway[1])])
            os.execv(f"./build/node", args)
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

    def register_round(self):
        timestamp = time.monotonic_ns()
        self.rounds.append((timestamp, list(self.peer_to_pid.keys())))

    def parse_logs(self):
        peer_state = dict()
        for peer in self.history_peers:
            peer_state[peer] = []
            try:
                # Parse checkpointed state of given node from the log file
                with open(f'{peer[0]}_{peer[1]}.log') as f:
                    for line in f.readlines():
                        if "PEERS" not in line:
                            continue
                        splits = line.split()
                        timestamp = parse_ts(splits[1])
                        peers = [parse_peer(splits[7+i]) for i in range(int(splits[5]))]
                        peer_state[peer].append((timestamp, peers))
            finally:
                pass

        return peer_state

    def compile_report(self):
        print(f'\n\n==========SIMULATION RAPORT==========')
        print(f'Simulation ran for {len(self.rounds)} rounds')

        peer_state = self.parse_logs()
        for idx, (round_ts, expected_peers) in enumerate(self.rounds):
            # get latest state of each expected peer with a ts <= round ts
            latest_state = dict()
            for peer in expected_peers:
                latest_state[peer] = set()

                while True:
                    if len(peer_state[peer]) == 0 or peer_state[peer][0][0] > round_ts:
                        break
                    latest_state[peer] = set(peer_state[peer][0][1])
                    peer_state[peer].pop(0)

            # for each peer, diff with expected
            expected_peers_set = set(expected_peers)
            print(f"\nRound {idx+1}:")
            for peer in expected_peers:
                intersection = len(latest_state[peer] & expected_peers_set)
                diff = len(latest_state[peer] - expected_peers_set)
                if intersection == len(expected_peers_set)-1 and diff == 0:
                    print(f'Node {peer}: OK')
                else:
                    print(f'Node {peer}: not OK, {diff} extra, {len(expected_peers_set)-1-intersection} missing')

    def cleanup(self):
        # delete log files
        for peer in self.history_peers:
            try:
                os.remove(f'{peer[0]}_{peer[1]}.log')
            finally:
                pass


def main():
    simulation = Simulation()

    # generate seeds + fork seeds
    seeds = simulation.generate_peers(NUM_SEEDS)
    for i in range(len(seeds)):
        simulation.start_seed(seeds[i], seeds[:i] + seeds[i+1:])

    time.sleep(GRACE_PERIOD)
    for round in range(NUM_ROUNDS):
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

        time.sleep(COOLDOWN)
        simulation.register_round()

    time.sleep(GRACE_PERIOD)
    peers = list(simulation.get_peers())
    for peer in peers:
        simulation.kill_peer(peer)

    simulation.compile_report()
    simulation.cleanup()


if __name__ == "__main__":
    main()
