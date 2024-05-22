import subprocess
import argparse

CONFIGS = [
    (
        {"seeds": 3, "grace": 3, "rounds": 10, "kills": 0, "joins": 0, "cooldown": 3},
        "no_issue",
    ),
    (
        {
            "seeds": 5,
            "grace": 5,
            "rounds": 10,
            "kills": 1,
            "joins": 1,
            "cooldown": 5,
        },
        "small_reliable",
    ),
    (
        {
            "seeds": 5,
            "grace": 5,
            "rounds": 10,
            "kills": 2,
            "joins": 2,
            "cooldown": 5,
        },
        "small_unreliable",
    ),
    (
        {
            "seeds": 10,
            "grace": 5,
            "rounds": 10,
            "kills": 1,
            "joins": 1,
            "cooldown": 10,
        },
        "big_reliable",
    ),
    (
        {
            "seeds": 10,
            "grace": 5,
            "rounds": 10,
            "kills": 4,
            "joins": 4,
            "cooldown": 10,
        },
        "big_unreliable",
    ),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--speed", required=True)

    args = parser.parse_args()
    protocol_speed = args.speed

    for config in CONFIGS:
        print(f"Running {config[1]}")
        with open(f"stress_test_results/{config[1]}_{protocol_speed}.txt", "w") as f:
            subprocess.run(
                [
                    "python3",
                    "stress_test.py",
                    "--seeds",
                    str(config[0]["seeds"]),
                    "--grace",
                    str(config[0]["grace"]),
                    "--rounds",
                    str(config[0]["rounds"]),
                    "--kills",
                    str(config[0]["kills"]),
                    "--joins",
                    str(config[0]["joins"]),
                    "--cooldown",
                    str(config[0]["cooldown"]),
                ],
                stdout=f,
            )


if __name__ == "__main__":
    main()
