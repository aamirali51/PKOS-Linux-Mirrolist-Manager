import subprocess
import tempfile
import os
import glob
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
from src.ui.dialogs import PasswordDialog


class SecureFileOperations:
    def __init__(self):
        self.mirrorlist_path = "/etc/pacman.d/mirrorlist"
        self.backup_pattern = "/etc/pacman.d/mirrorlist.backup.*"
        self._cached_password = None
        self._password_verified = False
    
    def get_existing_backups(self):
        """Get list of existing backup files."""
        try:
            backups = glob.glob(self.backup_pattern)
            backups.sort(reverse=True)  # Most recent first
            return [os.path.basename(backup) for backup in backups[:10]]  # Show last 10
        except Exception:
            return []
    
    def authenticate_user(self, operation="system operation", force_new=False):
        """Prompt user for password and validate it."""
        # Return cached password if available and not forcing new authentication
        if not force_new and self._password_verified and self._cached_password:
            return self._cached_password
        
        dialog = PasswordDialog(
            title="Authentication Required",
            message=f"Administrator privileges are required for {operation}.\nPlease enter your password:"
        )
        
        if dialog.exec() == dialog.DialogCode.Accepted:
            password = dialog.get_password()
            if password:
                # Test the password with a simple sudo command
                if self._test_password(password):
                    # Cache the verified password
                    self._cached_password = password
                    self._password_verified = True
                    return password
                else:
                    QMessageBox.critical(None, "Authentication Failed", 
                                       "Incorrect password. Please try again.")
                    return None
            else:
                return None
        else:
            return None
    
    def clear_cached_password(self):
        """Clear the cached password."""
        self._cached_password = None
        self._password_verified = False
    
    def _test_password(self, password):
        """Test if the provided password is correct."""
        try:
            # Test with a harmless sudo command
            process = subprocess.Popen(
                ['sudo', '-S', 'echo', 'test'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=10)
            return process.returncode == 0
            
        except Exception:
            return False
    
    def _run_sudo_command(self, command, password):
        """Run a sudo command with the provided password."""
        try:
            process = subprocess.Popen(
                ['sudo', '-S'] + command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(input=password + '\n', timeout=30)
            
            if process.returncode != 0:
                raise Exception(f"Command failed: {stderr}")
            
            return stdout
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("Command timed out")
        except Exception as e:
            raise Exception(f"Failed to execute command: {str(e)}")
    
    def create_backup(self, password=None):
        """Create a backup of the current mirrorlist."""
        if password is None:
            password = self.authenticate_user("creating backup")
            if password is None:
                return None
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"/etc/pacman.d/mirrorlist.backup.{timestamp}"
            
            # Create backup
            self._run_sudo_command(['cp', self.mirrorlist_path, backup_path], password)
            
            # Verify backup was created
            if self.verify_backup(backup_path, password):
                return backup_path
            else:
                raise Exception("Backup verification failed")
                
        except Exception as e:
            raise Exception(f"Failed to create backup: {str(e)}")
    
    def verify_backup(self, backup_path, password):
        """Verify that a backup file exists and is readable."""
        try:
            result = self._run_sudo_command(['test', '-f', backup_path], password)
            return True
        except Exception:
            return False
    
    def write_mirrorlist(self, selected_mirrors, password=None):
        """Write selected mirrors to the mirrorlist file."""
        if password is None:
            password = self.authenticate_user("updating mirrorlist")
            if password is None:
                return False
        
        try:
            # Create temporary file with new mirrorlist content
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.mirrorlist') as temp_file:
                temp_path = temp_file.name
                
                # Write header
                temp_file.write("##\n")
                temp_file.write("## Arch Linux repository mirrorlist\n")
                temp_file.write(f"## Generated by Arch Mirrorlist Manager on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                temp_file.write("##\n")
                temp_file.write("## Use 'pacman -Syy' to force pacman to refresh the package databases\n")
                temp_file.write("##\n\n")
                
                # Group mirrors by country
                mirrors_by_country = {}
                for mirror in selected_mirrors:
                    country = mirror.get('country', 'Unknown')
                    if country not in mirrors_by_country:
                        mirrors_by_country[country] = []
                    mirrors_by_country[country].append(mirror)
                
                # Write mirrors grouped by country
                for country, mirrors in sorted(mirrors_by_country.items()):
                    temp_file.write(f"## {country}\n")
                    for mirror in mirrors:
                        temp_file.write(f"Server = {mirror['url']}\n")
                    temp_file.write("\n")
            
            # Move the new mirrorlist to the correct location
            self._run_sudo_command(['mv', temp_path, self.mirrorlist_path], password)
            
            # Set proper permissions
            self._run_sudo_command(['chmod', '644', self.mirrorlist_path], password)
            
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise Exception(f"Failed to write mirrorlist: {str(e)}")
    
    def read_current_mirrorlist(self):
        """Read and return the current mirrorlist content."""
        try:
            with open(self.mirrorlist_path, "r") as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Failed to read mirrorlist: {str(e)}")
    
    def get_mirrorlist_info(self):
        """Get information about the current mirrorlist."""
        try:
            stat_info = os.stat(self.mirrorlist_path)
            return {
                'size': stat_info.st_size,
                'modified': datetime.fromtimestamp(stat_info.st_mtime),
                'exists': True
            }
        except Exception:
            return {'exists': False}