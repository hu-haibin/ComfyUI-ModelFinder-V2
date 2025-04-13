"""
License Management Module
Responsible for: license validation, device fingerprinting, activation code management
"""

import os
import re
import json
import time
import hashlib
import platform
import uuid
import subprocess
from datetime import datetime, timedelta

# License status constants
LICENSE_VALID = "valid"         # Valid license
LICENSE_EXPIRED = "expired"     # Expired license
LICENSE_INVALID = "invalid"     # Invalid license
LICENSE_TRIAL = "trial"         # Trial version
LICENSE_FREE = "free"           # Free version

# Membership levels
MEMBERSHIP_FREE = "free"        # Free membership
MEMBERSHIP_BASIC = "basic"      # Basic membership
MEMBERSHIP_PRO = "pro"          # Pro membership

# Configuration file path
def get_license_file_path():
    """Get license file path"""
    # Create configuration folder in user AppData directory
    app_data = os.getenv('APPDATA') or os.path.expanduser('~')
    config_dir = os.path.join(app_data, "ModelFinder")
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, "license.dat")

def get_hardware_id():
    """Generate unique hardware ID"""
    # Collect hardware information
    system_info = platform.uname()
    cpu_info = system_info.processor
    
    # Get motherboard UUID (Windows specific)
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["wmic", "csproduct", "get", "UUID"], capture_output=True, text=True)
            if result.returncode == 0:
                motherboard_id = result.stdout.strip().split("\n")[-1].strip()
            else:
                motherboard_id = ""
        else:
            motherboard_id = ""
    except:
        motherboard_id = ""
    
    # Get MAC address
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0, 8*6, 8)][::-1])
    except:
        mac = "00:00:00:00:00:00"
    
    # Combine hardware information and hash
    combined = f"{system_info.node}|{cpu_info}|{motherboard_id}|{mac}"
    return hashlib.sha256(combined.encode()).hexdigest()

class LicenseManager:
    """License Manager"""
    
    def __init__(self):
        """Initialize License Manager"""
        self.hardware_id = get_hardware_id()
        self.license_info = self._load_license()
        
        # Check if hardware ID matches
        if self.license_info and self.license_info.get("hardware_id") and self.license_info.get("hardware_id") != self.hardware_id:
            print("Hardware ID mismatch, license may have been transferred.")
            self.license_info["status"] = LICENSE_INVALID
    
    def _load_license(self):
        """Load license information"""
        license_file = get_license_file_path()
        if not os.path.exists(license_file):
            # Create default free version license
            default_license = {
                "status": LICENSE_FREE,
                "type": MEMBERSHIP_FREE,
                "usage": {
                    "single_analysis": {"total": 0, "today": 0, "last_date": ""},
                    "batch_analysis": {"total": 0, "today": 0, "last_date": ""}
                },
                "credits": 5,  # Initial gift of 5 credits
                "creation_date": datetime.now().strftime("%Y-%m-%d"),
                "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "hardware_id": self.hardware_id
            }
            self._save_license(default_license)
            return default_license
            
        try:
            with open(license_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check date, reset daily counts
            if data.get("usage"):
                today = datetime.now().strftime("%Y-%m-%d")
                
                for usage_type in data["usage"]:
                    last_date = data["usage"][usage_type].get("last_date", "")
                    if last_date != today:
                        data["usage"][usage_type]["today"] = 0
                        data["usage"][usage_type]["last_date"] = today
                
                self._save_license(data)  # Save updated usage data
                
            return data
        except Exception as e:
            print(f"Error loading license: {e}")
            return None
    
    def _save_license(self, license_data):
        """Save license information"""
        try:
            with open(get_license_file_path(), 'w', encoding='utf-8') as f:
                json.dump(license_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving license: {e}")
            return False
    
    def get_license_status(self):
        """Get license status"""
        if not self.license_info:
            return LICENSE_FREE
            
        return self.license_info.get("status", LICENSE_FREE)
    
    def get_membership_type(self):
        """Get membership type"""
        if not self.license_info:
            return MEMBERSHIP_FREE
            
        return self.license_info.get("type", MEMBERSHIP_FREE)
    
    def get_credits(self):
        """Get current credits"""
        if not self.license_info:
            return 0
            
        return self.license_info.get("credits", 0)
    
    def add_credits(self, amount):
        """Add credits"""
        if not self.license_info:
            return False
            
        current = self.license_info.get("credits", 0)
        self.license_info["credits"] = current + amount
        return self._save_license(self.license_info)
    
    def use_credits(self, amount):
        """Use credits
        
        Returns:
            bool: Whether credits were used successfully
        """
        if not self.license_info:
            return False
            
        current = self.license_info.get("credits", 0)
        if current < amount:
            return False  # Insufficient credits
            
        self.license_info["credits"] = current - amount
        return self._save_license(self.license_info)
    
    def can_use_feature(self, feature_type, credits_cost=0):
        """Check if the specified feature can be used
        
        Args:
            feature_type: Feature type ("single_analysis" or "batch_analysis")
            credits_cost: Number of credits required
        
        Returns:
            (bool, str): (Availability, Reason)
        """
        # Check license status
        status = self.get_license_status()
        if status == LICENSE_INVALID:
            return False, "License invalid"
        elif status == LICENSE_EXPIRED:
            return False, "License expired"
            
        # Get membership type and usage limits
        membership = self.get_membership_type()
        
        # Define limits for each membership type
        limits = {
            MEMBERSHIP_FREE: {"single_analysis": 3, "batch_analysis": 1},
            MEMBERSHIP_BASIC: {"single_analysis": 10, "batch_analysis": 3},
            MEMBERSHIP_PRO: {"single_analysis": float('inf'), "batch_analysis": float('inf')}
        }
        
        # Check if daily usage limit has been reached
        if feature_type in self.license_info.get("usage", {}):
            usage = self.license_info["usage"][feature_type]
            daily_limit = limits.get(membership, {}).get(feature_type, 0)
            
            if usage.get("today", 0) >= daily_limit and daily_limit != float('inf'):
                # Check if credits can be used
                if credits_cost > 0:
                    if self.get_credits() >= credits_cost:
                        # Return the specific reason code "Use Credits"
                        return True, "Use Credits"
                    else:
                        return False, "Insufficient credits"
                return False, f"Daily usage limit reached ({daily_limit} times)"
        
        return True, "Available"

    def record_usage(self, feature_type):
        """Record feature usage
        
        Args:
            feature_type: Feature type ("single_analysis" or "batch_analysis")
        
        Returns:
            bool: Whether recording was successful
        """
        if not self.license_info or "usage" not in self.license_info:
            return False
            
        # Ensure corresponding usage record exists
        if feature_type not in self.license_info["usage"]:
            self.license_info["usage"][feature_type] = {"total": 0, "today": 0, "last_date": ""}
            
        usage = self.license_info["usage"][feature_type]
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Check if date needs reset
        if usage.get("last_date", "") != today:
            usage["today"] = 0
            usage["last_date"] = today
            
        # Increment usage count
        usage["total"] = usage.get("total", 0) + 1
        usage["today"] = usage.get("today", 0) + 1
        
        # Save update
        return self._save_license(self.license_info)
    
    def validate_activation_code(self, activation_code):
        """Validate activation code
        
        Args:
            activation_code (str): Activation code
        
        Returns:
            (bool, str): (Is valid, Message)
        """
        # Simulated activation code validation logic
        # This is an example, replace with server validation logic in actual application
        # Simulated activation code format: TYPE-CREDITS-EXPIRY(YYYYMMDD) or TYPE-UNLIMITED
        # Example: BASIC-50-20251231, PRO-UNLIMITED
        
        parts = activation_code.upper().split('-')
        if len(parts) < 2 or len(parts) > 3:
            return False, "Invalid activation code format"
            
        license_type = parts[0].lower()
        if license_type not in [MEMBERSHIP_BASIC, MEMBERSHIP_PRO]:
            return False, "Unsupported membership type"
        
        # Placeholder for checking if code is already used/valid on a server
        # In this simulation, assume the code is valid for now
        is_code_valid_on_server = True # Replace with actual check
        if not is_code_valid_on_server:
             return False, "Activation code used or invalid"
        
        credits = 0
        expiry_date = None
        expiry_date_str = None
        unlimited = False
        
        if parts[1] == "UNLIMITED":
            unlimited = True
        elif len(parts) == 3:
            try:
                credits = int(parts[1])
                expiry_date_str = parts[2]
                expiry_date = datetime.strptime(expiry_date_str, "%Y%m%d")
            except ValueError:
                return False, "Invalid activation code format (credits/date)"
        else:
            return False, "Invalid activation code format"
            
        # Update license info
        self.license_info["type"] = license_type
        if unlimited:
            self.license_info["status"] = LICENSE_VALID # Pro unlimited is always valid
            self.license_info["expiry_date"] = None
        else:
            if expiry_date < datetime.now():
                self.license_info["status"] = LICENSE_EXPIRED
            else:
                self.license_info["status"] = LICENSE_VALID
            self.license_info["expiry_date"] = expiry_date.strftime("%Y-%m-%d")
        
        # Add credits if specified
        if credits > 0:
            self.add_credits(credits)
            
        # Ensure hardware ID is set
        self.license_info["hardware_id"] = self.hardware_id
        
        # Save updated license
        self._save_license(self.license_info)
        
        return True, f"Activation successful! Type: {license_type}, Credits added: {credits}, Expiry: {expiry_date_str if expiry_date_str else 'Unlimited'}"

    def check_daily_signin(self):
        """Daily sign-in check
        
        Returns:
            (bool, int): (Sign-in success, Credits gained)
        """
        if not self.license_info:
            return False, 0
            
        today = datetime.now().strftime("%Y-%m-%d")
        # Get last sign-in date
        last_signin = self.license_info.get("last_signin", "")
        
        if last_signin == today:
            return False, 0 # Already signed in today
            
        # Update sign-in date
        self.license_info["last_signin"] = today
        
        # Give different rewards based on membership type
        membership = self.get_membership_type()
        credits_earned = 0
        if membership == MEMBERSHIP_FREE:
            credits_earned = 1
        elif membership == MEMBERSHIP_BASIC:
            credits_earned = 3
        elif membership == MEMBERSHIP_PRO:
            credits_earned = 5
        
        # Add credits and save
        self.add_credits(credits_earned)
        self._save_license(self.license_info)
        
        print(f"Sign-in successful, earned {credits_earned} credits")
        return True, credits_earned

# Create a global license manager instance
license_manager = LicenseManager()

def run_test():
    """Test function"""
    manager = LicenseManager()
    print(f"Current Hardware ID: {manager.hardware_id}")
    print(f"License Status: {manager.get_license_status()}")
    print(f"Membership Type: {manager.get_membership_type()}")
    print(f"Current Credits: {manager.get_credits()}")
    
    # Test sign-in
    print("\nAttempting sign-in:")
    result, credits = manager.check_daily_signin()
    print(f"Sign-in result: {result}, Credits earned: {credits}")
    
    print("\nAttempting sign-in again:")
    result, credits = manager.check_daily_signin()
    print(f"Sign-in result: {result}, Credits earned: {credits}")
    
    # Test feature usage
    print("\nTesting feature usage (single analysis):")
    can_use, reason = manager.can_use_feature("single_analysis", 2)
    print(f"Usage result: {can_use}, Reason: {reason}")
    if can_use:
        if reason == "Use Credits":
            used = manager.use_credits(2)
            print(f"Credits used successfully: {used}")
            if used:
                 manager.record_usage("single_analysis")
        else:
            manager.record_usage("single_analysis")
            
    print(f"Current Credits after usage attempt: {manager.get_credits()}")
    
    # Test activation code
    print("\nAttempting activation code:")
    valid, msg = manager.validate_activation_code("BASIC-50-20251231")
    print(f"Activation result: {valid}, Message: {msg}")
    print(f"Credits after activation: {manager.get_credits()}")

if __name__ == "__main__":
    run_test()