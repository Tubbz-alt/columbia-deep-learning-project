import math

import numpy as np
# from tensorflow_core.python.keras import regularizers
# from tensorflow_core.python.keras.layers.core import Dense
# from tensorflow_core.python.keras.models import Sequential

import torch
from torch import nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

from game.game import Action
from networks.network import BaseNetwork


class VertexCoverNetwork(BaseNetwork):

    def __init__(self,
                 state_size: int,
                 action_size: int,
                 representation_size: int,
                 max_value: int,
                 hidden_neurons: int = 64,
                 weight_decay: float = 1e-4,
                 representation_activation: str = 'tanh'):
        self.state_size = state_size
        self.action_size = action_size
        self.value_support_size = math.ceil(math.sqrt(max_value)) + 1

        #regularizer = regularizers.l2(weight_decay)

        class Net(torch.nn.Module):
            def __init__(self):
                super(Net, self).__init__()
                self.conv1 = GCNConv(1, 16)
                self.conv2 = GCNConv(16, representation_size)

            def forward(self, data):
                x, edge_index = data.x, data.edge_index

                x = self.conv1(x, edge_index)
                x = F.relu(x)
                x = F.dropout(x, training=self.training)
                x = self.conv2(x, edge_index)

                #print('Representation outputted')

                return F.Tanh(x, dim=representation_size)

        representation_network = Net()
        value_network = nn.Sequential(nn.Linear(representation_size, hidden_neurons), nn.ReLU(),
                            nn.Linear(self.value_support_size, hidden_neurons))
        policy_network = nn.Sequential(nn.Linear(representation_size, hidden_neurons), nn.ReLU(),
                            nn.Linear(self.action_size, hidden_neurons))
        dynamic_network = nn.Sequential(nn.Linear(representation_size+self.action_size, hidden_neurons), nn.ReLU(),
                            nn.Linear(representation_size, hidden_neurons))
        reward_network = nn.Sequential(nn.Linear(representation_size+self.action_size, hidden_neurons), nn.ReLU(),
                            nn.Linear(1, hidden_neurons))


        # value_network = Sequential([Dense(hidden_neurons, activation='relu', kernel_regularizer=regularizer),
        #                             Dense(self.value_support_size, kernel_regularizer=regularizer)])
        # policy_network = Sequential([Dense(hidden_neurons, activation='relu', kernel_regularizer=regularizer),
        #                              Dense(action_size, kernel_regularizer=regularizer)])
        # dynamic_network = Sequential([Dense(hidden_neurons, activation='relu', kernel_regularizer=regularizer),
        #                               Dense(representation_size, activation=representation_activation,
        #                                     kernel_regularizer=regularizer)])
        # reward_network = Sequential([Dense(16, activation='relu', kernel_regularizer=regularizer),
        #                              Dense(1, kernel_regularizer=regularizer)])

        super().__init__(representation_network, value_network, policy_network, dynamic_network, reward_network)

    def _value_transform(self, value_support: np.array) -> float:
        """
        The value is obtained by first computing the expected value from the discrete support.
        Second, the inverse transform is then apply (the square function).
        """

        value = self._softmax(value_support)
        value = np.dot(value, range(self.value_support_size))
        value = np.asscalar(value) ** 2
        return value

    def _reward_transform(self, reward: np.array) -> float:
        return np.asscalar(reward)

    def _conditioned_hidden_state(self, hidden_state: np.array, action: Action) -> np.array:
        conditioned_hidden = np.concatenate((hidden_state, np.eye(self.action_size)[action.index]))
        return np.expand_dims(conditioned_hidden, axis=0)

    def _softmax(self, values):
        """Compute softmax using numerical stability tricks."""
        values_exp = np.exp(values - np.max(values))
        return values_exp / np.sum(values_exp)
