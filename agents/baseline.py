from typing import Dict


class BoustrophedonAgent:

    def __init__(self, cruise_altitude: float = 6.0):
        self.cruise_altitude = cruise_altitude

        # direction (right or left)
        self.direction = 1

    def decide(self, observation: Dict) -> Dict:
        position = observation['position']
        x, y, z = position

        local_map = observation['local_map']
        center = local_map.shape[0] // 2

        # ===== PEVNÝ "HADOVÝ" SKEN =====
        next_x = center + self.direction
        blocked = True
        if 0 <= next_x < local_map.shape[1]:
            cell = local_map[center, next_x]
            blocked = (cell == -1) or (int(cell) == 1)

        if blocked:
            self.direction *= -1
            move = (0, 1, 0)
        else:
            move = (self.direction, 0, 0)

        return {'move': move, 'altitude': self.cruise_altitude}

    def reset(self):
        self.direction = 1
        self.home_position = None