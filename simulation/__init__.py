"""
Simulation module: тільки запуск симуляцій
"""

from .simulation import Simulator
from .experiment_runner import ExperimentRunner

__all__ = [
    'Simulator',
    'ExperimentRunner'
]

__version__ = '1.0.0'