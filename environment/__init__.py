"""
Environment module: тільки DroneEnvironment з вбудованим CollisionDetector
"""

from .environment import DroneEnvironment, Terrain

__all__ = [
    'DroneEnvironment',
    'Terrain'
]

__version__ = '1.0.0'