import numpy as np
import seaborn as sns

from graphs import CompleteGraph, RandomGeometricGraph


class PushSumNode:
    def __init__(self, idx, val, neighbors):
        self.idx = idx
        self.x = val
        self.w = 1

    def main_loop(self, p):
        if p == self.idx:
            return None

        message = (self.idx, p, self.x / 2, self.w / 2)
        self.x /= 2
        self.w /= 2
        return message

    def on_update(self, msg):
        self.x += msg[2]
        self.w += msg[3]

    def get_estimate(self):
        return self.x / self.w


class PushFlowNode:
    def __init__(self, idx, val, neighbors):
        self.idx = idx
        self.x = val
        self.w = 1

        self.flows_x = [0 for _ in range(len(neighbors))]
        self.flows_w = [0 for _ in range(len(neighbors))]
        self.neighbor_to_idx = {x: i for (i, x) in enumerate(neighbors)}

    def main_loop(self, p):
        if p == self.idx:
            return None

        idx_p = self.neighbor_to_idx[p]
        self.flows_x[idx_p] = self.flows_x[idx_p] + (self.x - sum(self.flows_x)) / 2
        self.flows_w[idx_p] = self.flows_w[idx_p] + (self.w - sum(self.flows_w)) / 2

        # send updated estimate to p
        message = (self.idx, p, self.flows_x[idx_p], self.flows_w[idx_p])
        return message

    def on_update(self, msg):
        idx = self.neighbor_to_idx[msg[0]]
        self.flows_x[idx] = -msg[2]
        self.flows_w[idx] = -msg[3]

    def get_estimate(self):
        s_x = self.x - sum(self.flows_x)
        s_w = self.w - sum(self.flows_w)
        return s_x / s_w


def run_averaging(graph, mode, initial_values, rounds=30, msg_loss=0):
    mean = sum(initial_values) / graph.n

    nodes, rmses = [], []
    for i in range(graph.n):
        # create node i
        neigh = graph.get_neighbors(i)
        if mode == "PushSum":
            nodes.append(PushSumNode(i, initial_values[i], neigh))
        elif mode == "PushFlow":
            nodes.append(PushFlowNode(i, initial_values[i], neigh))

    for _ in range(rounds):
        messages = []
        for idx, node in enumerate(nodes):
            m = node.main_loop(graph.get_random_neighbor(idx))
            if m is not None:
                messages.append(m)

        # run msg loss
        messages_ = []
        for message in messages:
            r = np.random.rand()
            if r >= msg_loss:
                messages_.append(message)
        messages = messages_

        # apply updates
        for message in messages:
            nodes[message[1]].on_update(message)

        # get rmse
        current = 0
        for node in nodes:
            current += (mean - node.get_estimate()) ** 2

        rmses.append((current / graph.n) ** (1 / 2))

    return rmses


def test_push_sum_msg_loss():
    graph_size = 100

    for graph_type in ["K", "RG"]:
        if graph_type == "K":
            graph = CompleteGraph(graph_size, fixed_scheduling=False)
        else:
            graph = RandomGeometricGraph(graph_size, 0.5, fixed_scheduling=False)

        num_rounds = 200
        initial_values = np.random.randint(0, 100 + 1, size=graph_size)

        rounds_x, precision_y, msg_loss_k = [], [], []
        for msg_loss in [0, 0.25, 0.5]:
            rmses_push_sum = run_averaging(
                graph, "PushSum", initial_values, num_rounds, msg_loss
            )

            rounds_x.extend([x for x in range(num_rounds)])
            precision_y.extend(rmses_push_sum)
            msg_loss_k.extend([msg_loss for _ in range(num_rounds)])

        plot = sns.relplot(
            data={"Round": rounds_x, "RMSE": precision_y, "Loss": msg_loss_k},
            x="Round",
            y="RMSE",
            hue="Loss",
            # pallete=["blue", "red", "green"],
            kind="line",
            facet_kws={"legend_out": True},
        ).set(yscale="log")

        plot.savefig(
            f"Push_Sum_Msg_Loss_{graph_type}.pdf",
            format="pdf",
        )


def test_push_flow_vs_push_sum(test):
    graph_size = 100

    for graph_type in ["K", "RG"]:
        if graph_type == "K":
            graph = CompleteGraph(graph_size, fixed_scheduling=False)
            num_rounds = 2500
        else:
            graph = RandomGeometricGraph(graph_size, 0.5, fixed_scheduling=False)
            num_rounds = 1000

        initial_values = np.random.randint(0, 100 + 1, size=graph_size)

        rounds_x, precision_y, mode_k = [], [], []
        for msg_loss in [0.25, 0.5]:
            rmses_push_sum = run_averaging(
                graph, "PushSum", initial_values, num_rounds, msg_loss
            )

            rounds_x.extend([x for x in range(num_rounds)])
            precision_y.extend(rmses_push_sum)
            mode_k.extend([f"PushSum {msg_loss}" for _ in range(num_rounds)])

        for msg_loss in [0.25, 0.5]:
            rmses_push_sum = run_averaging(
                graph, "PushFlow", initial_values, num_rounds, msg_loss
            )

            rounds_x.extend([x for x in range(num_rounds)])
            precision_y.extend(rmses_push_sum)
            mode_k.extend([f"PushFlow {msg_loss}" for _ in range(num_rounds)])

        plot = sns.relplot(
            data={"Round": rounds_x, "RMSE": precision_y, "Mode": mode_k},
            x="Round",
            y="RMSE",
            hue="Mode",
            # pallete=["blue", "red", "green"],
            kind="line",
            facet_kws={"legend_out": True},
        ).set(yscale="log")

        plot.savefig(
            f"Push_flow_comparison_{graph_type}_{test}.pdf",
            format="pdf",
        )


if __name__ == "__main__":
    sns.set_theme()
    # test_push_sum_msg_loss()

    for i in range(20):
        test_push_flow_vs_push_sum(i)
