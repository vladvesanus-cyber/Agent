from typing import List


class HealthMonitor:
    """
    Follow the health of drone
    Update state according to paramaters
    """
    
    def __init__(self, battery, motors, sensors, structure):
        self.battery = battery
        self.motors = motors
        self.sensors = sensors
        self.structure = structure
        
        self.health_history = []
        self.last_update = {
            'energy_consumed': 0,
            'motor_stress': [0, 0, 0, 0],
            'altitude': 0,
            'collision_occurred': False,
            'collision_damage': 0,
            'ambient_temp': 25
        }
    
    def update(self,
               energy_consumed: float,
               motor_stress: List[float],
               altitude: float,
               collision_occurred: bool = False,
               collision_damage: float = 0.0,
               ambient_temp: float = 25.0):
        
        # Write last update
        self.last_update = {
            'energy_consumed': energy_consumed,
            'motor_stress': motor_stress,
            'altitude': altitude,
            'collision_occurred': collision_occurred,
            'collision_damage': collision_damage,
            'ambient_temp': ambient_temp
        }
        
        # Battery
        self._update_battery(energy_consumed, ambient_temp)
        
        # Motors
        self._update_motors(motor_stress, altitude, ambient_temp)
        
        # sensors
        self._update_sensors(altitude, collision_occurred, collision_damage)
        
        # structure
        if collision_occurred and collision_damage > 0:
            self._apply_collision_damage(collision_damage)
        
        # health
        self._calculate_overall_health()
    
    #Battery
    
    def _update_battery(
        self,
        energy_consumed: float,
        ambient_temp: float,
    ):
        """Update battery charge, temperature, and health."""

        self.battery.discharge(energy_consumed)

        heat = energy_consumed * 0.8

        self.battery.apply_thermal_stress(heat)

        cooling = (
            self.battery.temperature - ambient_temp
        ) * 0.05

        self.battery.temperature = max(
            ambient_temp,
            self.battery.temperature - cooling,
        )

        self.battery.update_health()
    
    # motors
    
    def _update_motors(self, motor_stress: List[float], altitude: float, ambient_temp: float):
        """Update motors"""
        
        for i, stress in enumerate(motor_stress):
            # apply stress
            self.motors.apply_stress(i, stress)
            
            # cool down worse in hight
            motor = self.motors.motors[i]
            altitude_factor = 1 + (altitude / 20) * 0.3
            
            cooling = (motor['temperature'] - ambient_temp) * 0.03 / altitude_factor
            motor['temperature'] = max(ambient_temp, motor['temperature'] - cooling)
        
        # update temperature
        self.motors.update_temperatures()
    
    # sensors
    
    def _update_sensors(self, altitude: float, 
                       collision_occurred: bool, 
                       collision_damage: float):
        
        for i, sensor in enumerate(self.sensors.sensors):
            # Dirt on low altitude
            if altitude <= 5:
                dust_factor = (5 - altitude) * 0.2
                self.sensors.apply_dirt(i, dust_factor * 0.1)
            
            if collision_occurred and collision_damage > 0:
                if sensor['type'] == 'camera':
                    dirt_amount = collision_damage * 20
                else:
                    dirt_amount = collision_damage * 10
                
                self.sensors.apply_dirt(i, dirt_amount)
    
    # Structure
    
    def _apply_collision_damage(self, collision_damage: float):
        
        # Divide damage to components
        propeller_damage = collision_damage * 30
        frame_damage = collision_damage * 20
        sensor_dirt = collision_damage * 25
        motor_stress_amount = collision_damage * 15
        thermal_stress = collision_damage * 10
        
        # Damage propellers
        for i in range(self.structure.num_propellers):
            self.structure.propeller_health[i] = max(
                0, 
                self.structure.propeller_health[i] - propeller_damage
            )
        
        # Damage structure
        self.structure.integrity = max(0, self.structure.integrity - frame_damage)
        
        # Apply dirt
        for i in range(len(self.sensors.sensors)):
            self.sensors.apply_dirt(i, sensor_dirt)
        
        # Apply stress on motors
        for i in range(len(self.motors.motors)):
            self.motors.motors[i]['wear'] += motor_stress_amount
        
        # Temperature stress
        self.battery.apply_thermal_stress(thermal_stress)
        
        # increase crash count
        self.structure.crash_count += 1
    
    # Health
    
    def _calculate_overall_health(self):
        battery_health = self.battery.health
        motor_health = self.motors.get_average_efficiency()
        sensor_health = self.sensors.get_average_accuracy()
        structure_health = self.structure.get_structural_integrity()
        
        overall = (
            battery_health * 0.3 +
            motor_health * 0.3 +
            sensor_health * 0.2 +
            structure_health * 0.2
        )
        
        self.health_history.append(overall)
    
    def get_overall_health(self) -> float:
        return self.health_history[-1] if self.health_history else 100.0
    
    def is_system_healthy(self) -> bool:
        return (
            self.battery.is_healthy() and
            self.structure.is_flightworthy()
        )
    
    def get_critical_alerts(self) -> List[str]:
        alerts = []
        
        # Battery
        if self.battery.temperature > 50:
            alerts.append("🔥 BATTERY OVERHEATED!")
        
        if self.battery.charge < 10:
            alerts.append("🔴 BATTERY CRITICAL!")
        
        # Motors
        if any(m['temperature'] > 70 for m in self.motors.motors):
            alerts.append("🔥 MOTORS OVERHEATED!")
        
        # Structure
        if not self.structure.is_flightworthy():
            alerts.append("❌ DRONE NOT FLIGHT-WORTHY!")
        
        if self.structure.integrity < 30:
            alerts.append("💥 STRUCTURE CRITICAL!")
        
        # Overall Health
        if self.get_overall_health() < 40:
            alerts.append("🚨 OVERALL HEALTH CRITICAL!")
        
        return alerts
    
    def reset(self):
        
        self.health_history = []
        self.last_update = {
            'energy_consumed': 0,
            'motor_stress': [0, 0, 0, 0],
            'altitude': 0,
            'collision_occurred': False,
            'collision_damage': 0,
            'ambient_temp': 25
        }
        initial_health = (100 * 0.3 + 100 * 0.3 + 90 * 0.2 + 100 * 0.2)
        self.health_history = [initial_health]