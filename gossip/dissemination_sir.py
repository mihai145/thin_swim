import numpy as np
import seaborn as sns

from graphs import CompleteGraph, RingGraph, RandomGeometricGraph
from nodes import run_sir

sns.set_theme()


# single run of SIR on a graph of size n
# experiments: compare convergence for various values of k
def single_run_sir(n, test=0):
    ks = [1, 2, 5, 10]

    for graph_type in ["K", "RandGeom"]:
        for mode in ["Push", "Pull", "PushPull"]:
            infected, removed, disseminated, messages = [], [], [], []
            for k in ks:
                if graph_type == "K":
                    graph = CompleteGraph(n, fixed_scheduling=False)
                else:
                    graph = RandomGeometricGraph(n, 0.5, fixed_scheduling=False)

                if mode == "Push":
                    inf, rem, msg = run_sir(graph, True, False, k=k)
                elif mode == "Pull":
                    inf, rem, msg = run_sir(graph, False, True, k=k)
                else:
                    inf, rem, msg = run_sir(graph, True, True, k=k)

                infected.append(inf)
                removed.append(rem)
                messages.append(msg)
                disseminated.append([inf[i] + rem[i] for i in range(len(inf))])

            cnt_rounds = max(
                len(infected[0]),
                len(infected[1]),
                len(infected[2]),
                len(infected[3]),
            )

            for output in ["abs", "percentage"]:
                x_tick_step = cnt_rounds // 10
                if output == "abs":
                    y = [x for v in disseminated for x in v]
                    y_label = "Infected"
                    y_lim, y_tick_step = n + 1, 500
                else:
                    y = [(x / n) * 100 for v in disseminated for x in v]
                    y_label = "Infected percentage"
                    y_lim, y_tick_step = 100, 10

                plot = (
                    sns.relplot(
                        data={
                            "Round": [x for v in infected for x in range(len(v))],
                            y_label: y,
                            "K": [
                                ks[i]
                                for i, v in enumerate(infected)
                                for _ in range(len(v))
                            ],
                        },
                        x="Round",
                        y=y_label,
                        hue="K",
                        palette=["green", "blue", "red", "black"],
                        kind="line",
                        facet_kws={"legend_out": False},
                    )
                    .set(xticks=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
                    .set(xticklabels=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
                    .set(yticks=[y for y in range(0, y_lim + 1, y_tick_step)])
                    .set(yticklabels=[y for y in range(0, y_lim + 1, y_tick_step)])
                )

                plot.ax.axvline(x=len(infected[0]) - 1, c="green", ls="--")
                plot.ax.axvline(x=len(infected[1]) - 1, c="blue", ls="--")
                plot.ax.axvline(x=len(infected[2]) - 1, c="red", ls="--")
                plot.ax.axvline(x=len(infected[3]) - 1, c="black", ls="--")

                if output == "percentage":
                    plot.ax.yaxis.set_major_formatter(lambda x, _: str(x) + "%")

                plot.savefig(
                    f"sir_{graph_type}_{n}_{mode}_single_{output}_{test}.pdf",
                    format="pdf",
                )


# multiple runs of SIR on a graph of size n
# experiments: compare convergence for various values of k vs SI model
def multiple_run_sir(n, num_rounds=50, test=0):
    ks = [1, 2, 10]

    for graph_type in ["K", "RandGeom"]:
        for mode in ["PushPull"]:
            infected, removed, disseminated, messages = [], [], [], []
            K = []
            for k in ks:
                for _ in range(num_rounds):
                    if graph_type == "K":
                        graph = CompleteGraph(n, fixed_scheduling=False)
                    else:
                        graph = RandomGeometricGraph(n, 0.5, fixed_scheduling=False)

                    if mode == "Push":
                        inf, rem, msg = run_sir(graph, True, False, k=k)
                    elif mode == "Pull":
                        inf, rem, msg = run_sir(graph, False, True, k=k)
                    else:
                        inf, rem, msg = run_sir(graph, True, True, k=k)

                    infected.append(inf)
                    removed.append(rem)
                    messages.append(msg)
                    disseminated.append([inf[i] + rem[i] for i in range(len(inf))])
                    K.extend([k for _ in range(len(inf))])

            cnt_rounds = max(len(v) for v in infected)

            for output in ["abs", "percentage"]:
                x_tick_step = cnt_rounds // 10
                if output == "abs":
                    y = [x for v in disseminated for x in v]
                    y_label = "Infected"
                    y_lim, y_tick_step = n + 1, 500
                else:
                    y = [(x / n) * 100 for v in disseminated for x in v]
                    y_label = "Infected percentage"
                    y_lim, y_tick_step = 100, 10

                plot = (
                    sns.relplot(
                        data={
                            "Round": [x for v in infected for x in range(len(v))],
                            y_label: y,
                            "K": K,
                        },
                        x="Round",
                        y=y_label,
                        hue="K",
                        palette=["green", "blue", "red", "black"],
                        kind="line",
                        facet_kws={"legend_out": False},
                    )
                    .set(xticks=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
                    .set(xticklabels=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
                    .set(yticks=[y for y in range(0, y_lim + 1, y_tick_step)])
                    .set(yticklabels=[y for y in range(0, y_lim + 1, y_tick_step)])
                )

                if output == "percentage":
                    plot.ax.yaxis.set_major_formatter(lambda x, _: str(x) + "%")

                plot.savefig(
                    f"sir_{graph_type}_{n}_{mode}_multiple_runs_{num_rounds}_{output}_{test}.pdf",
                    format="pdf",
                )


def compare_single_sir():
    # run multiple tests
    num_tests = 10
    for i in range(num_tests):
        single_run_sir(5000, i)
        print(f"Done test {i+1}/{num_tests}")


def compare_multiple_sir():
    # run multiple tests
    num_tests = 10
    for i in range(num_tests):
        multiple_run_sir(5000, 20, i)
        print(f"Done test {i+1}/{num_tests}")


if __name__ == "__main__":
    # compare_single_sir()
    # compare_multiple_sir()
    pass
