import numpy as np
import seaborn as sns

from graphs import CompleteGraph, RingGraph, RandomGeometricGraph
from nodes import run_si

sns.set_theme()


# single run of SI on a complete graph
# experiment 1: number of infected nodes vs number of rounds elapsed for Push, Pull, Push-Pull SI
# experiment 2: number of messages sent vs percentage of infected nodes for Push, Pull, Push-Pull SI
def run_complete_si_single(n):
    graph = CompleteGraph(n)

    infected_push, messages_push = run_si(graph, True, False, 0)
    graph.reset()
    infected_pull, messages_pull = run_si(graph, False, True, 0)
    graph.reset()
    infected_pp, messages_pp = run_si(graph, True, True, 0)
    graph.reset()

    # compare the number of rounds needed for dissemination
    r_push, r_pull, r_pp = len(infected_push), len(infected_pull), len(infected_pp)
    cnt_rounds = max(r_push, r_pull, r_pp)

    cnt_x_ticks, cnt_y_ticks = 10, 10

    x_tick_step = cnt_rounds // cnt_x_ticks
    y_tick_step = n // cnt_y_ticks

    plot = (
        sns.relplot(
            data={
                "Round": [x for x in range(r_push)]
                + [x for x in range(r_pull)]
                + [x for x in range(r_pp)],
                "Infected": infected_push + infected_pull + infected_pp,
                "Mode": ["Push" for x in range(r_push)]
                + ["Pull" for x in range(r_pull)]
                + ["Push-Pull" for x in range(r_pp)],
            },
            x="Round",
            y="Infected",
            hue="Mode",
            palette=["red", "green", "blue"],
            kind="line",
            facet_kws={"legend_out": False},
        )
        # .set(title=f"SI Gossip on Complete Graph of size {n}")
        .set(xticks=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
        .set(xticklabels=[x for x in range(0, cnt_rounds + 1, x_tick_step)])
        .set(yticks=[y for y in range(0, n + 1, y_tick_step)])
        .set(yticklabels=[y for y in range(0, n + 1, y_tick_step)])
    )

    plot.ax.axvline(x=r_push - 1, c="red", ls="--")
    plot.ax.axvline(x=r_pull - 1, c="green", ls="--")
    plot.ax.axvline(x=r_pp - 1, c="blue", ls="--")

    plot.savefig(f"si_complete_{n}_rounds.pdf", format="pdf")

    # compare the number of messages needed for dissemination
    # x-axis: percentage of infected nodes
    # y-axis: messages needed for such percentage
    m = max(messages_push[-1], messages_pull[-1], messages_pp[-1])
    y_tick_step = 10000
    x_tick_step = 100 // cnt_x_ticks

    plot = (
        sns.relplot(
            data={
                "Infected": [(x / n) * 100 for x in infected_push]
                + [(x / n) * 100 for x in infected_pull]
                + [(x / n) * 100 for x in infected_pp],
                "Messages": messages_push + messages_pull + messages_pp,
                "Mode": ["Push" for x in range(r_push)]
                + ["Pull" for x in range(r_pull)]
                + ["Push-Pull" for x in range(r_pp)],
            },
            x="Infected",
            y="Messages",
            hue="Mode",
            palette=["red", "green", "blue"],
            kind="line",
            legend=False,
        )
        # .set(title=f"SI Gossip on Complete Graph of size {n}")
        .set(xticks=[x for x in range(0, 100 + 1, x_tick_step)])
        .set(xticklabels=[x for x in range(0, 100 + 1, x_tick_step)])
        .set(yticks=[y for y in range(0, m + 1, y_tick_step)])
        .set(yticklabels=[y for y in range(0, m + 1, y_tick_step)])
    )

    plot.ax.axhline(y=messages_push[-1], c="red", ls="--")
    plot.ax.axhline(y=messages_pull[-1], c="green", ls="--")
    plot.ax.axhline(y=messages_pp[-1], c="blue", ls="--")

    plot.set_xticklabels(fontsize=8)
    plot.ax.xaxis.set_major_formatter(lambda x, _: str(x) + "%")

    plot.savefig(f"si_complete_{n}_messages.pdf", format="pdf")


# multiple runs of SI on a complete graph
# experiment 1: number of infected nodes (mean + std) vs number of rounds elapsed for Push, Pull, Push-Pull SI
# experiment 2: number of messages sent (mean + std) vs percentage of infected nodes for Push, Pull, Push-Pull SI
def run_complete_si_mean_std(n, num_rounds=10, test=0):
    infected_push, messages_push = [], []
    infected_pull, messages_pull = [], []
    infected_pp, messages_pp = [], []

    for i in range(num_rounds):
        graph = CompleteGraph(n)
        i_push, m_push = run_si(graph, True, False, 0)
        infected_push.append(i_push)
        messages_push.append(m_push)

        graph.reset()
        i_pull, m_pull = run_si(graph, False, True, 0)
        infected_pull.append(i_pull)
        messages_pull.append(m_pull)

        graph.reset()
        i_pp, m_pp = run_si(graph, True, True, 0)
        infected_pp.append(i_pp)
        messages_pp.append(m_pp)

        # print(f"Done round {i+1}/{num_rounds}")

    r_push, r_pull, r_pp = (
        np.array([len(v) for v in infected_push]),
        np.array([len(v) for v in infected_pull]),
        np.array([len(v) for v in infected_pp]),
    )
    r_push_mean, r_pull_mean, r_pp_mean = (
        np.mean(r_push),
        np.mean(r_pull),
        np.mean(r_pp),
    )
    r_push_std, r_pull_std, r_pp_std = np.std(r_push), np.std(r_pull), np.std(r_pp)

    # discard outliers
    max_r_push, min_r_push = (
        int(r_push_mean + r_push_std),
        int(r_push_mean - r_push_std) + 1,
    )
    max_r_pull, min_r_pull = (
        int(r_pull_mean + r_pull_std),
        int(r_pull_mean - r_pull_std) + 1,
    )
    max_r_pp, min_r_pp = int(r_pp_mean + r_pp_std), int(r_pp_mean - r_pp_std) + 1
    max_r = max(max_r_push, max_r_pull, max_r_pp)

    # extend
    for v in infected_push:
        v.extend([n for _ in range(max_r_push - len(v))])
    for v in infected_pull:
        v.extend([n for _ in range(max_r_pull - len(v))])
    for v in infected_pp:
        v.extend([n for _ in range(max_r_pp - len(v))])
    for v in messages_push:
        v.extend([v[-1] for _ in range(max_r_push - len(v))])
    for v in messages_pull:
        v.extend([v[-1] for _ in range(max_r_pull - len(v))])
    for v in messages_pp:
        v.extend([v[-1] for _ in range(max_r_pp - len(v))])

    rounds_x = (
        [
            x
            for v in infected_push
            for x in range(len(v))
            if min_r_push <= len(v) <= max_r_push
        ]
        + [
            x
            for v in infected_pull
            for x in range(len(v))
            if min_r_pull <= len(v) <= max_r_pull
        ]
        + [
            x
            for v in infected_pp
            for x in range(len(v))
            if min_r_pp <= len(v) <= max_r_pp
        ]
    )

    infected_y = (
        [x for v in infected_push for x in v if min_r_push <= len(v) <= max_r_push]
        + [x for v in infected_pull for x in v if min_r_pull <= len(v) <= max_r_pull]
        + [x for v in infected_pp for x in v if min_r_pp <= len(v) <= max_r_pp]
    )

    mode_legend = (
        [
            "Push"
            for v in infected_push
            for _ in range(len(v))
            if min_r_push <= len(v) <= max_r_push
        ]
        + [
            "Pull"
            for v in infected_pull
            for _ in range(len(v))
            if min_r_pull <= len(v) <= max_r_pull
        ]
        + [
            "Push-Pull"
            for v in infected_pp
            for _ in range(len(v))
            if min_r_pp <= len(v) <= max_r_pp
        ]
    )

    x_tick_step, y_tick_step = 2, 500
    plot = (
        sns.relplot(
            data={
                "Round": rounds_x,
                "Infected": infected_y,
                "Mode": mode_legend,
            },
            x="Round",
            y="Infected",
            hue="Mode",
            palette=["red", "green", "blue"],
            style="Mode",
            kind="line",
            facet_kws={"legend_out": False},
        )
        .set(xticks=[x for x in range(0, max_r + 1, x_tick_step)])
        .set(xticklabels=[x for x in range(0, max_r + 1, x_tick_step)])
        .set(yticks=[y for y in range(0, n + 1, y_tick_step)])
        .set(yticklabels=[y for y in range(0, n + 1, y_tick_step)])
    )

    plot.savefig(
        f"si_complete_{n}_runs_{num_rounds}_rounds_stddev_{test}.pdf", format="pdf"
    )

    # messages vs percentage of infected
    m = max(
        [max(v) for v in messages_push]
        + [max(v) for v in messages_pull]
        + [max(v) for v in messages_pp]
    )

    bin_size = 100
    infected_percentage = (
        [((x // bin_size) * bin_size // n) * 100 for v in infected_push for x in v]
        + [((x // bin_size) * bin_size // n) * 100 for v in infected_pull for x in v]
        + [((x // bin_size) * bin_size // n) * 100 for v in infected_pp for x in v]
    )
    messages = (
        [x for v in messages_push for x in v]
        + [x for v in messages_pull for x in v]
        + [x for v in messages_pp for x in v]
    )
    mode_legend = (
        ["Push" for v in messages_push for _ in range(len(v))]
        + ["Pull" for v in messages_pull for _ in range(len(v))]
        + ["Push-Pull" for v in messages_pp for _ in range(len(v))]
    )

    x_tick_step, y_tick_step = 10, 10000
    plot = (
        sns.relplot(
            data={
                "Infected": infected_percentage,
                "Messages": messages,
                "Mode": mode_legend,
            },
            x="Infected",
            y="Messages",
            hue="Mode",
            palette=["red", "green", "blue"],
            kind="line",
            facet_kws={"legend_out": False},
        )
        .set(xticks=[x for x in range(0, 100 + 1, x_tick_step)])
        .set(xticklabels=[x for x in range(0, 100 + 1, x_tick_step)])
        .set(yticks=[y for y in range(0, m + 1, y_tick_step)])
        .set(yticklabels=[y for y in range(0, m + 1, y_tick_step)])
    )

    plot.set_xticklabels(fontsize=8)
    plot.ax.xaxis.set_major_formatter(lambda x, _: str(x) + "%")

    plot.savefig(
        f"si_complete_{n}_runs_{num_rounds}_messages_stddev_{test}.pdf", format="pdf"
    )


# multiple runs of SI Push on a complete graph
# experiment 1: number of infected nodes (mean + 3std) vs number of rounds elapsed for Push SI, ideal 2^x
def compare_complete_si_exp(n, num_rounds=100):
    infected_push, messages_push = [], []
    for i in range(num_rounds):
        graph = CompleteGraph(n, fixed_scheduling=False)
        i_push, m_push = run_si(graph, True, False, 0)
        infected_push.append(i_push)
        messages_push.append(m_push)

    max_r_push = max([len(r) for r in infected_push])

    mean_push, std_push = [], []
    for i in range(max_r_push):
        vals = np.array([x[i] for x in infected_push if i < len(x)])
        mean_push.append(np.mean(vals))
        std_push.append(np.std(vals))

    # 2^x
    idx_ideal, ideal = [0], [1]
    while ideal[-1] * 2 <= n:
        idx_ideal.append(idx_ideal[-1] + 1)
        ideal.append(ideal[-1] * 2)
    idx_ideal.append(np.log2(n))
    ideal.append(n)

    x_tick_step, y_tick_step = 2, 500
    plot = (
        sns.relplot(
            data={
                "Round": [x for x in range(max_r_push)] + idx_ideal,
                "Infected": mean_push + ideal,
                "Mode": ["Push" for x in range(max_r_push)]
                + ["2^x" for x in range(len(ideal))],
            },
            x="Round",
            y="Infected",
            hue="Mode",
            palette=["red", "black"],
            style="Mode",
            kind="line",
            facet_kws={"legend_out": False},
        )
        .set(xticks=[x for x in range(0, max_r_push + 1, x_tick_step)])
        .set(xticklabels=[x for x in range(0, max_r_push + 1, x_tick_step)])
        .set(yticks=[y for y in range(0, n + 1, y_tick_step)])
        .set(yticklabels=[y for y in range(0, n + 1, y_tick_step)])
    )

    # shade 3 std deviations
    mean_push, std_push = np.array(mean_push), np.array(std_push)
    plot.ax.fill_between(
        x=[x for x in range(max_r_push)],
        y1=mean_push - 3 * std_push,
        y2=mean_push + 3 * std_push,
        color="red",
        alpha=0.3,
    )

    # half of nodes infected
    plot.ax.axhline(y=n // 2, c="black", ls="-.", alpha=0.5)

    plot.savefig(
        f"si_complete_{n}_runs_{num_rounds}_compare_push_ideal.pdf", format="pdf"
    )


# multiple runs of SI Pull on a complete graph
# experiment 1: number of rounds necessary for second phase (mean + std) vs graph size for Pull SI, ideal log(log(x))
def compare_complete_si_loglog(num_rounds=10):
    graph_sizes = [2**2, 2**4, 2**6, 2**8, 2**10, 2**12, 2**14, 2**16, 2**18, 2**20]

    rounds_left = []
    for graph_size in graph_sizes:
        graph = CompleteGraph(graph_size, fixed_scheduling=False)

        for i in range(num_rounds):
            infected_pull, _ = run_si(graph, False, True)
            for idx, cnt_infected in enumerate(infected_pull):
                if cnt_infected >= graph_size / 2:
                    rounds_left.append(len(infected_pull) - idx)
                    break

        print(f"Done graphs with size {graph_size}")

    plot = sns.relplot(
        data={
            "Graph size": [sz for sz in graph_sizes for _ in range(num_rounds)]
            + graph_sizes,
            "Rounds untill completion": rounds_left
            + [np.log(np.log(x)) for x in graph_sizes],
            "Mode": ["Pull" for x in range(len(graph_sizes) * num_rounds)]
            + ["log(log(x))" for x in range(len(graph_sizes))],
        },
        x="Graph size",
        y="Rounds untill completion",
        hue="Mode",
        palette=["green", "black"],
        style="Mode",
        kind="line",
        facet_kws={"legend_out": False},
    ).set(xscale="log")

    plot.savefig(f"si_complete_runs_{num_rounds}_compare_pull_ideal.pdf", format="pdf")


# multiple runs of SI Push, Pull and Push-Pull on a complete graph
# experiments 1..7: number of rounds necessary for dissemination vs graph size
def complete_si_vs_graph_size(num_rounds=50):
    graph_sizes = [
        2**5,
        2**6,
        2**7,
        2**8,
        2**9,
        2**10,
        2**11,
        2**12,
        2**13,
        2**14,
        2**15,
        2**16,
        2**17,
    ]

    rounds_push, rounds_pull, rounds_pp = [], [], []
    for graph_size in graph_sizes:
        for _ in range(num_rounds):
            graph = CompleteGraph(graph_size)

            i_push, _ = run_si(graph, True, False)
            rounds_push.append(len(i_push))
            graph.reset()

            i_pull, _ = run_si(graph, False, True)
            rounds_pull.append(len(i_pull))
            graph.reset()

            i_pp, _ = run_si(graph, True, True)
            rounds_pp.append(len(i_pp))

        print(f"Done graphs for size {graph_size}")

    for modes in [
        ["Push"],
        ["Pull"],
        ["PP"],
        ["Push", "Pull", "PP"],
        ["Push", "Pull"],
        ["Push", "PP"],
        ["Pull", "PP"],
    ]:
        graph_size_x, rounds_y, mode_legend = [], [], []
        modes_str, pallete = "", []

        if "Push" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_push
            mode_legend += ["Push" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "push_"
            pallete += ["red"]

        if "Pull" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pull
            mode_legend += ["Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pull_"
            pallete += ["green"]

        if "PP" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pp
            mode_legend += ["Push-Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pp_"
            pallete += ["blue"]

        max_r, y_tick_step = max(rounds_y), 3
        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds untill completion": rounds_y,
                    "Mode": mode_legend,
                },
                x="Graph size",
                y="Rounds untill completion",
                hue="Mode",
                palette=pallete,
                kind="line",
                facet_kws={"legend_out": False},
            )
            .set(xscale="log")
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
        )

        plot.savefig(
            f"complete_si_vs_graph_size_runs_{num_rounds}_{modes_str}.pdf", format="pdf"
        )


# multiple runs of SI on a complete graph
# experiments 1..7: number of rounds necessary to finish phase 1 vs graph size
# experiments 8..14: number of rounds necessary to finish phase 2 vs graph size
def compare_complete_si_phases(num_rounds=10):
    graph_sizes = [
        2**5,
        2**6,
        2**7,
        2**8,
        2**9,
        2**10,
        2**11,
        2**12,
        2**13,
        2**14,
        2**15,
        2**16,
        2**17,
    ]

    rounds_push_p1, rounds_pull_p1, rounds_pp_p1 = [], [], []
    rounds_push_p2, rounds_pull_p2, rounds_pp_p2 = [], [], []
    for graph_size in graph_sizes:
        for _ in range(num_rounds):
            graph = CompleteGraph(graph_size)

            i_push, _ = run_si(graph, True, False)
            for idx, infected in enumerate(i_push):
                if infected >= graph_size / 2:
                    rounds_push_p1.append(idx)
                    rounds_push_p2.append(len(i_push) - idx - 1)
                    break
            graph.reset()

            i_pull, _ = run_si(graph, False, True)
            for idx, infected in enumerate(i_pull):
                if infected >= graph_size / 2:
                    rounds_pull_p1.append(idx)
                    rounds_pull_p2.append(len(i_pull) - idx - 1)
                    break
            graph.reset()

            i_pp, _ = run_si(graph, True, True)
            for idx, infected in enumerate(i_pp):
                if infected >= graph_size / 2:
                    rounds_pp_p1.append(idx)
                    rounds_pp_p2.append(len(i_pp) - idx - 1)
                    break

        print(f"Done graphs for size {graph_size}")

    for phase in [1, 2]:
        for modes in [
            ["Push"],
            ["Pull"],
            ["PP"],
            ["Push", "Pull", "PP"],
            ["Push", "Pull"],
            ["Push", "PP"],
            ["Pull", "PP"],
        ]:
            graph_size_x, rounds_y, mode_legend = [], [], []
            modes_str, pallete = "", []

            if "Push" in modes:
                graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
                if phase == 1:
                    rounds_y += rounds_push_p1
                else:
                    rounds_y += rounds_push_p2
                mode_legend += ["Push" for _ in range(len(graph_sizes) * num_rounds)]
                modes_str += "push_"
                pallete += ["red"]

            if "Pull" in modes:
                graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
                if phase == 1:
                    rounds_y += rounds_pull_p1
                else:
                    rounds_y += rounds_pull_p2
                mode_legend += ["Pull" for _ in range(len(graph_sizes) * num_rounds)]
                modes_str += "pull_"
                pallete += ["green"]

            if "PP" in modes:
                graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
                if phase == 1:
                    rounds_y += rounds_pp_p1
                else:
                    rounds_y += rounds_pp_p2
                mode_legend += [
                    "Push-Pull" for _ in range(len(graph_sizes) * num_rounds)
                ]
                modes_str += "pp_"
                pallete += ["blue"]

            max_r = max(rounds_y)
            if phase == 1:
                y_label = "Rounds for first phase"
            else:
                y_label = "Rounds for second phase"

            if max_r <= 10:
                y_tick_step = 1
            else:
                y_tick_step = 2

            plot = (
                sns.relplot(
                    data={
                        "Graph size": graph_size_x,
                        y_label: rounds_y,
                        "Mode": mode_legend,
                    },
                    x="Graph size",
                    y=y_label,
                    hue="Mode",
                    palette=pallete,
                    kind="line",
                    facet_kws={"legend_out": False},
                )
                .set(xscale="log")
                .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
                .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
            )

            plot.savefig(
                f"complete_si_vs_graph_size_runs_{num_rounds}_{modes_str}_{phase}_phase.pdf",
                format="pdf",
            )


# multiple runs of SI on a ring graph
# experiments 1..7: number of rounds needed for dissemination vs graph size (Push, Pull and Push-Pull variants)
def ring_si_vs_graph_size(num_rounds=10, test=0):
    graph_sizes = [10, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500]

    rounds_push, rounds_pull, rounds_pp = [], [], []
    messages_push, messages_pull, messages_pp = [], [], []
    for graph_size in graph_sizes:
        for _ in range(num_rounds):
            graph = RingGraph(graph_size)

            i_push, m_push = run_si(graph, True, False)
            rounds_push.append(len(i_push))
            messages_push.append(m_push[-1])
            graph.reset()

            i_pull, m_pull = run_si(graph, False, True)
            rounds_pull.append(len(i_pull))
            messages_pull.append(m_pull[-1])
            graph.reset()

            i_pp, m_pp = run_si(graph, True, True)
            rounds_pp.append(len(i_pp))
            messages_pp.append(m_pp[-1])

        print(f"Done graphs for size {graph_size}")

    for modes in [
        ["Push"],
        ["Pull"],
        ["PP"],
        ["Push", "Pull", "PP"],
        ["Push", "Pull"],
        ["Push", "PP"],
        ["Pull", "PP"],
    ]:
        graph_size_x, rounds_y, messages_y, mode_legend = [], [], [], []
        modes_str, pallete = "", []

        if "Push" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_push
            messages_y += messages_push
            mode_legend += ["Push" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "push_"
            pallete += ["red"]

        if "Pull" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pull
            messages_y += messages_pull
            mode_legend += ["Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pull_"
            pallete += ["green"]

        if "PP" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pp
            messages_y += messages_pp
            mode_legend += ["Push-Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pp_"
            pallete += ["blue"]

        # rounds vs graph size
        max_r, y_tick_step, x_tick_step = max(rounds_y), 50, 50
        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds untill completion": rounds_y,
                    "Mode": mode_legend,
                },
                x="Graph size",
                y="Rounds untill completion",
                hue="Mode",
                palette=pallete,
                kind="line",
                facet_kws={"legend_out": False},
            )
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 500 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 500 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"ring_si_vs_graph_size_runs_{num_rounds}_{modes_str}_rounds_{test}.pdf",
            format="pdf",
        )

        # messages vs graph size
        max_m, y_tick_step = max(messages_y), 30000
        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Messages": messages_y,
                    "Mode": mode_legend,
                },
                x="Graph size",
                y="Messages",
                hue="Mode",
                palette=pallete,
                kind="line",
                facet_kws={"legend_out": False},
            )
            # .set(xscale="log")
            .set(yticks=[y for y in range(0, max_m + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_m + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 500 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 500 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"ring_si_vs_graph_size_runs_{num_rounds}_{modes_str}_messages_{test}.pdf",
            format="pdf",
        )


# multiple runs of SI on a random geometric graph
# experiments 1..7: number of rounds needed for dissemination vs graph size (Push, Pull and Push-Pull variants)
def rand_geom_si_vs_graph_size(num_rounds=10, test=0):
    graph_sizes = [10, 100, 200, 300, 500, 750, 1000, 1250, 1500, 1750, 2000]

    rounds_push, rounds_pull, rounds_pp = [], [], []
    messages_push, messages_pull, messages_pp = [], [], []
    for graph_size in graph_sizes:
        for _ in range(num_rounds):
            graph = RandomGeometricGraph(graph_size, 0.5)

            i_push, m_push = run_si(graph, True, False)
            rounds_push.append(len(i_push))
            messages_push.append(m_push[-1])
            graph.reset()

            i_pull, m_pull = run_si(graph, False, True)
            rounds_pull.append(len(i_pull))
            messages_pull.append(m_pull[-1])
            graph.reset()

            i_pp, m_pp = run_si(graph, True, True)
            rounds_pp.append(len(i_pp))
            messages_pp.append(m_pp[-1])

        print(f"Done graphs for size {graph_size}")

    for modes in [
        ["Push"],
        ["Pull"],
        ["PP"],
        ["Push", "Pull", "PP"],
        ["Push", "Pull"],
        ["Push", "PP"],
        ["Pull", "PP"],
    ]:
        graph_size_x, rounds_y, messages_y, mode_legend = [], [], [], []
        modes_str, pallete = "", []

        if "Push" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_push
            messages_y += messages_push
            mode_legend += ["Push" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "push_"
            pallete += ["red"]

        if "Pull" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pull
            messages_y += messages_pull
            mode_legend += ["Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pull_"
            pallete += ["green"]

        if "PP" in modes:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_pp
            messages_y += messages_pp
            mode_legend += ["Push-Pull" for _ in range(len(graph_sizes) * num_rounds)]
            modes_str += "pp_"
            pallete += ["blue"]

        # rounds vs graph size
        max_r, y_tick_step, x_tick_step = max(rounds_y), 2, 200
        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds untill completion": rounds_y,
                    "Mode": mode_legend,
                },
                x="Graph size",
                y="Rounds untill completion",
                hue="Mode",
                palette=pallete,
                kind="line",
                facet_kws={"legend_out": False},
            )
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 2000 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 2000 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"rand_geom_si_vs_graph_size_runs_{num_rounds}_{modes_str}_rounds_{test}.pdf",
            format="pdf",
        )

        # messages vs graph size
        max_m = max(messages_y)
        if max_m <= 20000:
            y_tick_step = 2000
        else:
            y_tick_step = 3000
        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Messages": messages_y,
                    "Mode": mode_legend,
                },
                x="Graph size",
                y="Messages",
                hue="Mode",
                palette=pallete,
                kind="line",
                facet_kws={"legend_out": False},
            )
            # .set(xscale="log")
            .set(yticks=[y for y in range(0, max_m + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_m + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 2000 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 2000 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"rand_geom_si_vs_graph_size_runs_{num_rounds}_{modes_str}_messages_{test}.pdf",
            format="pdf",
        )


# multiple runs of SI on K, Ring and Random Geometric graphs
# experiments 1..3: number of rounds needed for dissemination vs graph size (comparing topologies against each other)
def si_rounds_vs_graph_size_compare_topologies(num_rounds=10, test=0):
    graph_sizes = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

    rounds_k, rounds_r, rounds_rg = [], [], []
    for graph_size in graph_sizes:
        for _ in range(num_rounds):
            k = CompleteGraph(graph_size)
            i_k, _ = run_si(k, True, True)
            rounds_k.append(len(i_k))

            r = RingGraph(graph_size)
            i_r, _ = run_si(r, True, True)
            rounds_r.append(len(i_r))

            rg = RandomGeometricGraph(graph_size, 0.5)
            i_rg, _ = run_si(rg, True, True)
            rounds_rg.append(len(i_rg))

    for graph_types in [["K", "R"], ["K", "RG"], ["R", "RG"]]:
        graph_size_x, rounds_y, graph_type_hue = [], [], []
        pallete, graph_types_str = [], ""

        if "K" in graph_types:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_k
            graph_type_hue += [
                "Complete" for _ in graph_sizes for _ in range(num_rounds)
            ]
            pallete += ["red"]
            graph_types_str += "k_"

        if "R" in graph_types:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_r
            graph_type_hue += ["Ring" for _ in graph_sizes for _ in range(num_rounds)]
            pallete += ["green"]
            graph_types_str += "g_"

        if "RG" in graph_types:
            graph_size_x += [sz for sz in graph_sizes for _ in range(num_rounds)]
            rounds_y += rounds_rg
            graph_type_hue += [
                "Rand. geometric" for _ in graph_sizes for _ in range(num_rounds)
            ]
            pallete += ["green"]
            graph_types_str += "rg_"

        max_r, x_tick_step = max(rounds_y), 100
        if max_r >= 500:
            y_tick_step = 100
        else:
            y_tick_step = 1

        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds untill completion": rounds_y,
                    "Graph": graph_type_hue,
                },
                x="Graph size",
                y="Rounds untill completion",
                hue=graph_type_hue,
                palette=["red", "green", "blue"],
                kind="line",
                facet_kws={"legend_out": False},
            )
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 1000 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 1000 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"topology_si_runs_{num_rounds}_{graph_types_str}_{test}.pdf",
            format="pdf",
        )


# multiple rounds of SI on K, Ring and Random Geometric with Message Loss
# experiments K, R, RG: number of rounds for dissemination vs graph size (comparing various message loss percentages)
def si_rounds_vs_graph_size_msg_loss(num_rounds=100, test=0):
    graph_sizes = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    msg_loss_pb = [0, 0.1, 0.2, 0.3, 0.4, 0.5]

    for graph_type in ["K", "R", "RG"]:
        graph_size_x, rounds_y, msg_loss = [], [], []

        for graph_size in graph_sizes:
            for prob in msg_loss_pb:
                for _ in range(num_rounds):
                    if graph_type == "K":
                        graph = CompleteGraph(graph_size, fixed_scheduling=False)
                    elif graph_type == "R":
                        graph = RingGraph(graph_size, fixed_scheduling=False)
                    elif graph_type == "RG":
                        graph = RandomGeometricGraph(
                            graph_size, 0.5, fixed_scheduling=False
                        )

                    i_pp, _ = run_si(graph, True, True, msg_loss=prob)
                    graph_size_x.append(graph_size)
                    rounds_y.append(len(i_pp))
                    msg_loss.append(prob)

                    # print(f"Done for size={graph_size} and prob={msg_loss_pb}")

        max_r, x_tick_step = max(rounds_y), 100
        if max_r >= 500:
            y_tick_step = 150
        else:
            y_tick_step = 2

        plot = (
            sns.relplot(
                data={
                    "Graph size": graph_size_x,
                    "Rounds untill completion": rounds_y,
                    "Msg. Loss probability": msg_loss,
                },
                x="Graph size",
                y="Rounds untill completion",
                hue="Msg. Loss probability",
                palette=["green", "blue", "orange", "red", "brown", "black"],
                kind="line",
                facet_kws={"legend_out": True},
            )
            .set(yticks=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(yticklabels=[y for y in range(0, max_r + 1, y_tick_step)])
            .set(xticks=[y for y in range(0, 1000 + 1, x_tick_step)])
            .set(xticklabels=[y for y in range(0, 1000 + 1, x_tick_step)])
        )
        plot.set_xticklabels(fontsize=9)

        plot.savefig(
            f"msg_loss_si_runs_{num_rounds}_{graph_type}_{test}.pdf",
            format="pdf",
        )


def run_experiments_complete_graph():
    run_complete_si_single(5000)

    # run multiple times
    for i in range(50):
        run_complete_si_mean_std(5000, num_rounds=50, test=i)

    compare_complete_si_exp(5000, 50)
    compare_complete_si_loglog(100)
    complete_si_vs_graph_size(100)
    compare_complete_si_phases(100)


def run_experiments_ring_graph():
    # run multiple times
    tests = 10
    for i in range(tests):
        ring_si_vs_graph_size(50, test=i)
        print(f"Done test {i+1}/{tests}")


def run_experiments_rand_geom_graph():
    # run multiple times
    tests = 10
    for i in range(tests):
        rand_geom_si_vs_graph_size(num_rounds=100, test=i)
        print(f"Done test {i+1}/{tests}")


def run_experiments_convergence_on_different_graphs():
    # run multiple times
    tests = 10
    for i in range(tests):
        si_rounds_vs_graph_size_compare_topologies(num_rounds=100, test=i)
        print(f"Done test {i+1}/{tests}")


def run_experiments_convergence_with_message_loss():
    # run multiple times
    tests = 10
    for i in range(tests):
        si_rounds_vs_graph_size_msg_loss(num_rounds=50, test=i)
        print(f"Done test {i+1}/{tests}")


if __name__ == "__main__":
    # run_experiments_complete_graph()
    # run_experiments_ring_graph()
    # run_experiments_rand_geom_graph()
    # run_experiments_convergence_on_different_graphs()
    # run_experiments_convergence_with_message_loss()
    pass
