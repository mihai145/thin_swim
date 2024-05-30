import numpy as np


class SINode:
    def __init__(self, idx, push, pull):
        self.idx = idx
        self.push = push
        self.pull = pull
        self.state = "S"

    def infect(self):
        self.state = "I"

    def run_main_loop(self, p):
        if p == self.idx:
            return []

        messages = []
        if self.push and self.state == "I":
            # send update to p
            messages.append((0, self.idx, p))

        if self.pull:
            # send update-request to p
            messages.append((1, self.idx, p))

        return messages

    def run_on_update(self):
        if self.state == "S":
            self.state = "I"

    def run_on_update_request(self, s):
        if self.state == "I":
            # reply with update to s
            return (0, self.idx, s)
        return None


def run_si(graph, push=True, pull=True, start_node=0, msg_loss=0.0):
    # initialize nodes
    nodes = []
    for i in range(graph.n):
        nodes.append(SINode(i, push, pull))

    nodes[start_node].infect()

    # keep track of the number of infected nodes and messages sent for each round
    infected, sent_messages = [1], [0]
    while True:
        # run main loop for each node and collect messages
        messages = []
        for i in range(graph.n):
            p = graph.get_random_neighbor(i)
            messages.extend(nodes[i].run_main_loop(p))

        cnt_messages_sent = len(messages)

        # run msg loss
        r = np.random.rand(len(messages))
        messages_ = []
        for idx, msg in enumerate(messages):
            if r[idx] > msg_loss:
                messages_.append(msg)
        messages = messages_

        # reply to all update request messages
        update_messages = []
        for message in messages:
            if message[0] == 0:
                update_messages.append(message)
            else:
                reply = nodes[message[2]].run_on_update_request(message[1])
                if reply is not None:
                    cnt_messages_sent += 1

                    # run msg loss for update-request replies
                    r = np.random.rand()
                    if r > msg_loss:
                        update_messages.append(reply)

        # apply updates
        for message in update_messages:
            nodes[message[2]].run_on_update()

        # update statistics for current round
        cnt_infected = 0
        for i in range(graph.n):
            if nodes[i].state == "I":
                cnt_infected += 1

        infected.append(cnt_infected)
        sent_messages.append(sent_messages[-1] + cnt_messages_sent)

        # all nodes have received the information
        if cnt_infected == graph.n:
            break

    return (infected, sent_messages)


def run_si_async(graph, push=True, pull=True, start_node=0, msg_loss=0.0):
    # initialize nodes
    nodes = []
    for i in range(graph.n):
        nodes.append(SINode(i, push, pull))

    nodes[start_node].infect()

    # keep track of the number of infected nodes and messages sent for each round
    infected, sent_messages = [1], [0]

    # keep track of pending messages for each round
    current_round = 0
    messages_for_round = dict()

    while True:
        if current_round not in messages_for_round:
            messages_for_round[current_round] = []

        # run main loop for each node and collect messages
        messages = []
        for i in range(graph.n):
            p = graph.get_random_neighbor(i)
            messages.extend(nodes[i].run_main_loop(p))

        cnt_messages_sent = len(messages)

        # run msg loss
        r = np.random.rand(len(messages))
        messages_ = []
        for idx, msg in enumerate(messages):
            if r[idx] > msg_loss:
                messages_.append(msg)
        messages = messages_

        # run msg delay
        for msg in messages:
            delay = np.random.randint(3, 5 + 1)
            if current_round + delay not in messages_for_round:
                messages_for_round[current_round + delay] = [msg]
            else:
                messages_for_round[current_round + delay].append(msg)

        # reply to all update request messages that arrive this round
        for message in messages_for_round[current_round]:
            if message[0] == 1:
                reply = nodes[message[2]].run_on_update_request(message[1])
                if reply is not None:
                    cnt_messages_sent += 1

                    # run msg loss for update-request replies
                    r = np.random.rand()
                    if r > msg_loss:
                        # run msg delay
                        delay = np.random.randint(3, 5 + 1)
                        if current_round + delay not in messages_for_round:
                            messages_for_round[current_round + delay] = [reply]
                        else:
                            messages_for_round[current_round + delay].append(reply)

        # apply updates
        for message in messages_for_round[current_round]:
            if message[0] == 0:
                nodes[message[2]].run_on_update()

        # update statistics for current round
        cnt_infected = 0
        for i in range(graph.n):
            if nodes[i].state == "I":
                cnt_infected += 1

        infected.append(cnt_infected)
        sent_messages.append(sent_messages[-1] + cnt_messages_sent)

        # all nodes have received the information
        if cnt_infected == graph.n:
            break

        current_round += 1

    return (infected, sent_messages)


class SIRNode:
    def __init__(self, idx, push, pull, k):
        self.idx = idx
        self.push = push
        self.pull = pull
        self.state = "S"
        self.k = k

    def infect(self):
        self.state = "I"

    def run_main_loop(self, p):
        if p == self.idx:
            return []

        messages = []
        if self.push and self.state == "I":
            # send update to p
            messages.append((0, self.idx, p))

        if self.pull:
            # send update-request to p
            messages.append((1, self.idx, p))

        return messages

    def run_on_update(self, s):
        if self.state == "S":
            self.state = "I"
            return None
        else:
            # reply with feedback to s
            return (2, self.idx, s)

    def run_on_update_request(self, s):
        if self.state == "I":
            # reply with update to s
            return (0, self.idx, s)
        return None

    def run_on_feedback(self):
        r = np.random.rand()
        if r <= 1 / self.k:
            self.state = "R"


def run_sir(graph, push=True, pull=True, start_node=0, k=1):
    # initialize nodes
    nodes = []
    for i in range(graph.n):
        nodes.append(SIRNode(i, push, pull, k))

    nodes[start_node].infect()

    # keep track of the number of infected nodes and messages sent for each round
    infected, removed, sent_messages = [1], [0], [0]
    while True:
        # run main loop for each node and collect messages
        messages = []
        for i in range(graph.n):
            p = graph.get_random_neighbor(i)
            messages.extend(nodes[i].run_main_loop(p))

        cnt_messages_sent = len(messages)

        # reply to all update request messages
        update_messages = []
        for message in messages:
            if message[0] == 0:
                update_messages.append(message)
            else:
                reply = nodes[message[2]].run_on_update_request(message[1])
                if reply is not None:
                    cnt_messages_sent += 1
                    update_messages.append(reply)

        # apply updates
        feedbacks = []
        for message in update_messages:
            r = nodes[message[2]].run_on_update(message[1])
            if r is not None:
                feedbacks.append(r)

        # apply feedbacks
        for feedback in feedbacks:
            cnt_messages_sent += 1
            nodes[feedback[2]].run_on_feedback()

        # update statistics for current round
        cnt_infected, cnt_removed = 0, 0
        for i in range(graph.n):
            if nodes[i].state == "I":
                cnt_infected += 1
            elif nodes[i].state == "R":
                cnt_removed += 1

        infected.append(cnt_infected)
        removed.append(cnt_removed)
        sent_messages.append(sent_messages[-1] + cnt_messages_sent)

        # all nodes are R (or S) or all nodes have received the update
        if cnt_infected == 0 or cnt_infected + cnt_removed == graph.n:
            break

    return (infected, removed, sent_messages)
