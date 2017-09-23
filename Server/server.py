import d2env
import tensorflow as tf
from keras import backend as K

GPU = True
CPU = False
num_cores = 4

if GPU:
    num_GPU = 1
    num_CPU = 1
if CPU:
    num_CPU = 1
    num_GPU = 0

config = tf.ConfigProto(intra_op_parallelism_threads=num_cores, \
                        inter_op_parallelism_threads=num_cores, allow_soft_placement=True, \
                        device_count = {'CPU' : num_CPU, 'GPU' : num_GPU})
session = tf.Session(config=config)
K.set_session(session)

import random
import gym
import math
import numpy as np
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from keras.utils import plot_model

class D2Solver():
    def __init__(self, n_episodes=1000, n_win_ticks=195, max_env_steps=None, gamma=1.0, epsilon=1.0, epsilon_min=0.01, epsilon_log_decay=0.995, alpha=0.01, alpha_decay=0.01, batch_size=4096, minibatches_per_episode=5, monitor=False, quiet=False):
        self.memory = deque(maxlen=1000000)
        self.positive_memory = deque(maxlen=1000000)
        self.positive_batch_injection = 10
        self.env = gym.make('dota2-v0')
        if monitor: self.env = gym.wrappers.Monitor(self.env, '../data/cartpole-1', force=True)
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_log_decay
        self.alpha = alpha
        self.alpha_decay = alpha_decay
        self.n_episodes = n_episodes
        self.n_win_ticks = n_win_ticks
        self.batch_size = batch_size
        self.quiet = quiet
        self.minibatches_per_episode = minibatches_per_episode
        if max_env_steps is not None: self.env._max_episode_steps = max_env_steps

        # Init model
        self.model = Sequential()
        self.model.add(Dense(self.env.observation_space.n*2, input_dim=self.env.observation_space.n, activation='linear'))
        self.model.add(Dense(self.env.observation_space.n, activation='linear'))
        self.model.add(Dense(self.env.observation_space.n, activation='tanh'))
        self.model.add(Dense(self.env.observation_space.n, activation='softmax'))
        self.model.add(Dense(self.env.action_space.n, activation='linear'))
        self.model.compile(loss='mse', optimizer=Adam(lr=self.alpha, decay=self.alpha_decay))
        #plot_model(self.model, to_file='models/last_episode.png')
        self.dump_model(0)

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def choose_action(self, state, epsilon):
        return self.env.action_space.sample() if (np.random.random() <= epsilon) else np.argmax(self.model.predict(state))

    def get_epsilon(self, t):
        return max(self.epsilon_min, min(self.epsilon, 1.0 - math.log10((t + 1) * self.epsilon_decay)))

    def preprocess_state(self, state):
        return np.reshape(state, [1, self.env.observation_space.n])

    def replay(self, batch_size):
        #print("replay")
        x_batch, y_batch = [], []
        minibatch = random.sample(
            self.memory, min(len(self.memory), batch_size))

        # we have very sparse rewards, so trying this to propagate it faster
        minibatch += random.sample(
            self.positive_memory, min(len(self.positive_memory), self.positive_batch_injection))
        for state, action, reward, next_state, done in minibatch:
            y_target = self.model.predict(state)
            y_target[0][action] = reward if done else reward + self.gamma * np.max(self.model.predict(next_state)[0])
            x_batch.append(state[0])
            y_batch.append(y_target[0])

        self.model.fit(np.array(x_batch), np.array(y_batch), batch_size=len(x_batch), verbose=0)

    def dump_model(self, e):
        self.model.save('models/episode_' + str(e) + '.bin')
        # print("Layer weights")
        # for layer in self.model.layers:
        #     weights = layer.get_weights()
        #     print(weights)

    def run(self):
        scores = deque(maxlen=100)

        for e in range(self.n_episodes):
            state = self.preprocess_state(self.env.reset())
            done = False
            totalReward = 0
            while not done:
                action = self.choose_action(state, self.get_epsilon(e))
                next_state, reward, done, _ = self.env.step(action)
                next_state = self.preprocess_state(next_state)
                self.remember(state, action, reward, next_state, done)
                if reward > 0:
                    self.positive_memory.append((state, action, reward, next_state, done))
                state = next_state
                totalReward += reward

            scores.append(totalReward)
            mean_score = np.mean(scores)
            if mean_score >= self.n_win_ticks and e >= 100:
                if not self.quiet: print('Ran {} episodes. Solved after {} trials ?'.format(e, e - 100))
                return e - 100
            #if e % 100 == 0 and not self.quiet:
            print('[Episode {}] - Score {} Mean score for last 100 {} Positive memories {}/{}'.format(e, totalReward, mean_score, len(self.positive_memory), len(self.memory)))

            for i in range(self.minibatches_per_episode):
                self.replay(self.batch_size)
            if self.epsilon > self.epsilon_min:
                self.epsilon *= self.epsilon_decay
            #plot_model(self.model, to_file='models/episode_' + str(e) + '.png')
            #plot_model(self.model, to_file='models/last_episode.png')
            self.dump_model(e)

        if not self.quiet: print('Did not solve after {} episodes ?'.format(e))
        return e

if __name__ == '__main__':
    agent = D2Solver()
    agent.run()