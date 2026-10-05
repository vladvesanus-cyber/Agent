"""
BoustrophedonAgent - základný (baseline) agent.

Lieta klasickým "hadovým" (snake / lawnmower) vzorom: riadok napravo,
o riadok nižšie, riadok naľavo, ... Rozhodnutie o smere NEZÁVISÍ od
aktuálnych vnemov (percepts) - iba od interného počítadla riadku.
Výšku letu má fixnú (nad korunami stromov), takže stromy neobchádza
a prekážky na trase rieši len tak, že predčasne preskočí na ďalší riadok.

Slúži ako referenčný ("hlúpy") agent pre porovnanie s AdaptiveHeightAgent
v experimentoch (Simulator / ExperimentRunner).
"""

from typing import Dict, Tuple


class BoustrophedonAgent:
    """
    Základný agent so pevne daným skenovacím vzorom (bez využitia vnemov
    na rozhodovanie o smere).
    """

    def __init__(self, cruise_altitude: float = 6.0, return_altitude: float = 2.0):
        """
        Args:
            cruise_altitude: výška letu nad korunami stromov pri skenovaní
            return_altitude: výška letu pri návrate domov (úspora energie)
        """
        self.cruise_altitude = cruise_altitude
        self.return_altitude = return_altitude

        # Interný stav - smer aktuálneho riadku (1 = vpravo, -1 = vľavo)
        self.direction = 1
        self.home_position = None

    def decide(self, observation: Dict) -> Dict:
        position = observation['position']
        x, y, z = position

        if self.home_position is None:
            self.home_position = observation.get('home_position', (x, y))

        battery = observation['health']['battery']['charge_percent']
        local_map = observation['local_map']
        center = local_map.shape[0] // 2

        # ===== REŽIM NÁVRATU DOMOV (rovnaký prah ako u adaptívneho agenta) =====
        if battery < 30:
            return self._go_home(position)

        # ===== NAJPRV VYSTÚPAŤ NA CESTOVNÚ VÝŠKU =====
        # Bez tejto fázy by sa dron pri štarte tesne pri strome mohol
        # zaseknúť: pod výškou 1 m je každý strom neprejazdná prekážka a
        # simulátor pri kolízii zablokuje pohyb aj zmenu výšky naraz.
        if z < self.cruise_altitude - 0.5:
            return {'move': (0, 0, 0), 'altitude': self.cruise_altitude}

        # ===== PEVNÝ "HADOVÝ" SKEN =====
        next_x = center + self.direction
        blocked = True
        if 0 <= next_x < local_map.shape[1]:
            cell = local_map[center, next_x]
            # Na cestovnej výške prekáža iba tvrdá prekážka alebo hranica mapy;
            # stromy aj tak preletí (lieta nad korunami) - práve preto sem-tam
            # klipne konár, keď koruna zasahuje vyššie než očakáva.
            blocked = (cell == -1) or (int(cell) == 1)

        if blocked:
            # "Pozrel sa, ako naskenoval riadok" a ide na ďalší - ale smer
            # ďalšieho pohybu stále určuje iba parita riadku, nie obsah vnemu.
            self.direction *= -1
            move = (0, 1, 0)
        else:
            move = (self.direction, 0, 0)

        return {'move': move, 'altitude': self.cruise_altitude}

    def _go_home(self, position: Tuple[float, float, float]) -> Dict:
        x, y, z = position
        hx, hy = self.home_position

        dx = -1 if x > hx else (1 if x < hx else 0)
        dy = -1 if y > hy else (1 if y < hy else 0)
        dz = -1 if z > self.return_altitude else 0

        return {'move': (dx, dy, dz), 'altitude': self.return_altitude}

    def reset(self):
        self.direction = 1
        self.home_position = None