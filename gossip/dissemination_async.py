import numpy as np
import seaborn as sns

from graphs import CompleteGraph, RingGraph, RandomGeometricGraph
from nodes import run_si, run_si_async

sns.set_theme()


# compare SI sync and async convergence on a graph of size n
# experiments: cnt infected vs number of rounds
def compare_sync_async_multiple(n, num_rounds=1, test=0):
    msg_loss = [0, 0.2, 0.5, "async"]

    for graph_type in ["K", "RG"]:
        round_x, infected_y, K = [], [], []
        rounds_0, rounds_02, rounds_05, rounds_async = 0, 0, 0, 0
        for loss in msg_loss:
            for _ in range(num_rounds):
                if graph_type == "K":
                    graph = CompleteGraph(n, fixed_scheduling=False)
                else:
                    graph = RandomGeometricGraph(n, rad=0.5, fixed_scheduling=False)

                if loss != "async":
                    inf, _ = run_si(graph, True, True, msg_loss=loss)
                    if loss == 0:
                        rounds_0 = len(inf)
                    elif loss == 0.2:
                        rounds_02 = len(inf)
                    else:
                        rounds_05 = len(inf)
                    K.extend([str(loss) for _ in range(len(inf))])
                else:
                    inf, _ = run_si_async(graph, True, True, msg_loss=0)
                    rounds_async = len(inf)
                    K.extend([str(loss) for _ in range(len(inf))])

                round_x.extend([x for x in range(len(inf))])
                infected_y.extend(inf)

        max_r = max(rounds_0, rounds_02, rounds_02, rounds_async)
        y_tick_step, x_tick_step = 500, max_r // 10
        if max_r >= 1000:
            x_tick_step = 100
        plot = (
            sns.relplot(
                data={
                    "Round": round_x,
                    "Infected": infected_y,
                    "K": K,
                },
                x="Round",
                y="Infected",
                hue="K",
                palette=["green", "blue", "red", "black"],
                kind="line",
                facet_kws={"legend_out": True},
            )
            .set(xticks=[x for x in range(0, max_r + 1, x_tick_step)])
            .set(xticklabels=[x for x in range(0, max_r + 1, x_tick_step)])
            .set(yticks=[y for y in range(0, 5000 + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, 5000 + 1, y_tick_step)])
        )

        if num_rounds == 1:
            plot.ax.axvline(x=rounds_0 - 1, c="green", ls="--")
            plot.ax.axvline(x=rounds_02 - 1, c="blue", ls="--")
            plot.ax.axvline(x=rounds_05 - 1, c="red", ls="--")
            plot.ax.axvline(x=rounds_async - 1, c="black", ls="--")

        if max_r >= 200:
            plot.set_xticklabels(fontsize=8)

        plot.savefig(
            f"si_async_{graph_type}_{n}_runs_{num_rounds}_{test}.pdf",
            format="pdf",
        )


# compare SI sync and async convergence on graphs of increasing size
# experiments: number of rounds vs graph size
def compare_async_vs_graph_size(num_rounds=1, test=0):
    msg_loss = [0, 0.2, 0.5, "async"]
    graph_sizes = [x for x in range(50, 1000 + 1, 50)]

    for graph_type in ["K", "RG"]:
        graph_size_x, rounds_y, K = [], [], []
        for graph_size in graph_sizes:
            for loss in msg_loss:
                for _ in range(num_rounds):
                    if graph_type == "K":
                        graph = CompleteGraph(graph_size, fixed_scheduling=False)
                    else:
                        graph = RandomGeometricGraph(
                            graph_size, rad=0.5, fixed_scheduling=False
                        )

                    if loss != "async":
                        inf, _ = run_si(graph, True, True, msg_loss=loss)
                        K.append(loss)
                    else:
                        inf, _ = run_si_async(graph, True, True, msg_loss=0)
                        K.append(str(loss))

                    graph_size_x.append(graph_size)
                    rounds_y.append(len(inf))

        max_r = max(rounds_y)
        y_tick_step, x_tick_step = max(rounds_y) // 10, 100

        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds": rounds_y,
                    "K": K,
                },
                x="Graph size",
                y="Rounds",
                hue="K",
                palette=["green", "blue", "red", "black"],
                kind="line",
                facet_kws={"legend_out": True},
            )
            .set(xticks=[x for x in range(0, 1000 + 1, x_tick_step)])
            .set(xticklabels=[x for x in range(0, 1000 + 1, x_tick_step)])
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
        )

        plot.savefig(
            f"si_async_{graph_type}_vs_size_runs_{num_rounds}_{test}.pdf",
            format="pdf",
        )


def compare_on_single_graph():
    num_tests = 10
    for i in range(num_tests):
        compare_sync_async_multiple(5000, 1, i)
        print(f"Done test {i+1}/{num_tests}")

    num_tests = 10
    for i in range(num_tests):
        compare_sync_async_multiple(5000, 20, i)
        print(f"Done test {i+1}/{num_tests}")


def compare_vs_graph_size():
    num_tests = 10
    for i in range(num_tests):
        compare_async_vs_graph_size(20, i)
        print(f"Done test {i+1}/{num_tests}")


if __name__ == "__main__":
    # compare_on_single_graph()
    # compare_vs_graph_size()
    pass
