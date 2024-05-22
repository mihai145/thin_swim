import subprocess
import time
from dataclasses import dataclass
from subprocess import DEVNULL
from typing import Dict, List, Tuple

import numpy as np


@dataclass
class ExperimentConfig:
    seeds: int
    kills: int
    joins: int
    rounds: int
    cooldown: int
    name: str


# configs = [
#     ExperimentConfig(3, 0, 0, 10, 3, "no_issue"),
#     ExperimentConfig(5, 1, 1, 10, 5, "small_reliable"),
#     ExperimentConfig(5, 2, 2, 10, 5, "small_unreliable"),
#     ExperimentConfig(10, 1, 1, 10, 10, "big_reliable"),
#     ExperimentConfig(10, 4, 4, 10, 10, "big_unreliable"),
# ]

configs = [
    ExperimentConfig(3, 0, 0, 10, 6, "no_issue"),
    ExperimentConfig(5, 1, 1, 10, 10, "small_reliable"),
    ExperimentConfig(5, 2, 2, 10, 10, "small_unreliable"),
    ExperimentConfig(10, 1, 1, 10, 20, "big_reliable"),
    ExperimentConfig(10, 4, 4, 10, 20, "big_unreliable"),
]


class SerfSimulation:
    current_name: str
    current_bind_port: int
    current_rpc_port: int
    name_to_ports: Dict[str, Tuple[int, int]]
    name_to_popen: Dict[str, subprocess.Popen]
    raports: List[str]

    def __init__(self):
        self.current_name = "aaaaa"
        self.current_bind_port = 5001
        self.current_rpc_port = 7373
        self.name_to_ports = dict()
        self.name_to_popen = dict()
        self.raports = []

    def gen_rand_name(self) -> str:
        prev_name = self.current_name

        # "increment" current name
        for i in range(len(self.current_name) - 1, -1, -1):
            if self.current_name[i] != "z":
                chars = list(self.current_name)
                chars[i] = chr(ord(self.current_name[i]) + 1)
                self.current_name = "".join(chars)
                break

        return prev_name

    def generate_and_add_member(self) -> Tuple[str, int, int]:
        name = self.gen_rand_name()
        self.name_to_ports[name] = (self.current_bind_port, self.current_rpc_port)
        self.current_bind_port, self.current_rpc_port = (
            self.current_bind_port + 1,
            self.current_rpc_port + 1,
        )
        return name, self.current_bind_port - 1, self.current_rpc_port - 1

    def start_seeds(self, cnt_seeds: int):
        for _ in range(cnt_seeds):
            name, bind_port, rpc_port = self.generate_and_add_member()
            self.name_to_popen[name] = subprocess.Popen(
                [
                    "./serf",
                    "agent",
                    f"-node={name}",
                    f"-bind=127.0.0.1:{bind_port}",
                    f"-rpc-addr=127.0.0.1:{rpc_port}",
                ],
                stdout=DEVNULL,
            )
            print(f"Started seed {name} {bind_port} {rpc_port}")

        time.sleep(1)
        gateway_tcp, gateway_udp = (
            next(iter(self.name_to_ports.values()))[0],
            next(iter(self.name_to_ports.values()))[1],
        )
        for _, udp_port in self.name_to_ports.values():
            if udp_port != gateway_udp:
                subprocess.run(
                    [
                        "./serf",
                        "join",
                        f"-rpc-addr=127.0.0.1:{udp_port}",
                        f"127.0.0.1:{gateway_tcp}",
                    ]
                )
        print("Joined seeds")

    def get_nodes(self) -> List[str]:
        return list(self.name_to_ports.keys())

    def kill_node(self, name: str):
        self.name_to_popen[name].kill()
        del self.name_to_ports[name]
        del self.name_to_popen[name]
        print(f"Killed node {name}")

    def join_node(self):
        name, bind_port, rpc_port = self.generate_and_add_member()
        gateway = next(iter(self.name_to_ports.values()))[0]

        self.name_to_popen[name] = subprocess.Popen(
            [
                "./serf",
                "agent",
                f"-node={name}",
                f"-bind=127.0.0.1:{bind_port}",
                f"-rpc-addr=127.0.0.1:{rpc_port}",
                f"-join=127.0.0.1:{gateway}",
            ],
            stdout=DEVNULL,
        )
        print(f"Joined node {name} {bind_port} {rpc_port}")

    def register_round(self):
        gateway = next(iter(self.name_to_ports.values()))[1]
        print(f"Gateway agent asked for members: {gateway}")
        completed_process = subprocess.run(
            ["./serf", "members", f"-rpc-addr=127.0.0.1:{gateway}"], capture_output=True
        )

        out = completed_process.stdout.decode("utf-8")
        expected, got = set(k for k in self.name_to_ports.keys()), set()

        for line in out.split("\n"):
            print(line)
            if "alive" in line:
                got.add(line[:5])

        if expected != got:
            self.raports.append(
                f"Not ok, {len(got - expected)} extra, {len(expected - got)} missing"
            )
        else:
            self.raports.append(
                f"Ok, {len(got - expected)} extra, {len(expected - got)} missing"
            )

    def compile_report(self) -> List[str]:
        return self.raports

    def destroy(self):
        for v in self.name_to_popen.values():
            v.kill()


def run_experiment(config: ExperimentConfig):
    print(f"Running {config.name}")

    simulation = SerfSimulation()
    simulation.start_seeds(config.seeds)
    time.sleep(3)

    for _ in range(config.rounds):
        nodes = simulation.get_nodes()

        # kill nodes
        to_kill = np.random.choice(len(nodes), size=config.kills, replace=False)
        for idx in to_kill:
            simulation.kill_node(nodes[idx])

        # join nodes
        for _ in range(config.joins):
            simulation.join_node()

        # wait and register round
        time.sleep(config.cooldown)
        simulation.register_round()

    simulation.destroy()

    report = simulation.compile_report()
    with open(f"{config.name}.txt", "w") as f:
        for line in report:
            f.write(f"{line}\n")


def main():
    for config in configs:
        run_experiment(config)
        time.sleep(10)


if __name__ == "__main__":
    main()
