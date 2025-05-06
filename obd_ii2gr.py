import obd
from datetime import datetime
import csv

# Custom PIDs for Toyota 2GR-FE/FKS engines
CUSTOM_PIDS = {
    "VVT_ANGLE_BANK1": {
        "command": "221160",
        "bytes": 4,
        "decode": lambda data: (int(data[2:4], 16) / 128.0) - 50  # Degrees
    },
    "VVT_ANGLE_BANK2": {
        "command": "221165",
        "bytes": 4,
        "decode": lambda data: (int(data[2:4], 16) / 128.0) - 50
    },
    "FUEL_TRIM_CELL": {
        "command": "221150",
        "bytes": 2,
        "decode": lambda data: int(data, 16)  # Current fuel trim cell (0-22)
    },
    "AF_CORRECTION": {
        "command": "221154",
        "bytes": 4,
        "decode": lambda data: (int(data[2:4], 16) - 128) # %
    }
}

class Toyota2GRDiagnostics:
    def __init__(self):
        self.connection = None
        self.connect_obd()
        self.register_custom_pids()
        
    def connect_obd(self):
        try:
            self.connection = obd.OBD()
            if not self.connection.is_connected():
                raise ConnectionError("Failed to connect to OBD-II")
            print("Connected to 2GR engine")
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.connection = None
    
    def register_custom_pids(self):
        if not self.connection:
            return
            
        for pid_name, config in CUSTOM_PIDS.items():
            cmd = obd.OBDCommand(
                pid_name,
                f"Toyota {pid_name}",
                config["command"],
                config["bytes"],
                config["decode"]
            )
            obd.protocols.ECU.add_command(cmd)
    
    def get_2gr_specific_data(self):
        if not self.connection:
            return None
            
        data = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "rpm": self._get_standard_pid(obd.commands.RPM),
            "coolant_temp": self._get_standard_pid(obd.commands.COOLANT_TEMP),
            "vvt_bank1": self._get_custom_pid("VVT_ANGLE_BANK1"),
            "vvt_bank2": self._get_custom_pid("VVT_ANGLE_BANK2"),
            "fuel_trim_cell": self._get_custom_pid("FUEL_TRIM_CELL"),
            "af_correction": self._get_custom_pid("AF_CORRECTION"),
            "throttle_pos": self._get_standard_pid(obd.commands.THROTTLE_POS),
            "short_term_ft": self._get_standard_pid(obd.commands.SHORT_FUEL_TRIM_1),
            "long_term_ft": self._get_standard_pid(obd.commands.LONG_FUEL_TRIM_1)
        }
        return data
    
    def _get_standard_pid(self, cmd):
        response = self.connection.query(cmd)
        return response.value.magnitude if response.value else None
    
    def _get_custom_pid(self, pid_name):
        try:
            cmd = obd.commands[pid_name]
            response = self.connection.query(cmd)
            return response.value
        except:
            return None
    
    def log_to_csv(self, filename="2gr_log.csv"):
        data = self.get_2gr_specific_data()
        if not data:
            return False
            
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(data)
        return True

    def monitor_vvt_synchronization(self, duration=60):
        """Check for VVT system issues common in 2GR engines"""
        start_time = time.time()
        vvt_errors = 0
        
        while time.time() - start_time < duration:
            data = self.get_2gr_specific_data()
            if not data:
                continue
                
            # Check VVT angle difference between banks
            if (data["vvt_bank1"] is not None and data["vvt_bank2"] is not None):
                angle_diff = abs(data["vvt_bank1"] - data["vvt_bank2"])
                if angle_diff > 5.0:  # Degrees threshold
                    vvt_errors += 1
                    print(f"VVT misalignment detected: {angle_diff:.1f}°")
            
            # Check for stuck VVT (common 2GR issue)
            if data["rpm"] > 3000 and abs(data["vvt_bank1"]) < 5.0:
                print("Possible stuck VVT solenoid (Bank 1)")
            
            time.sleep(1)
        
        print(f"VVT monitoring complete. Errors detected: {vvt_errors}")

# Usage
if __name__ == "__main__":
    diag = Toyota2GRDiagnostics()
    
    if diag.connection:
        # Real-time monitoring
        diag.monitor_vvt_synchronization()
        
        # Continuous logging
        while True:
            diag.log_to_csv()
            time.sleep(5)