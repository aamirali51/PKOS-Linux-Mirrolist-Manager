import subprocess
import json
import re
from typing import List, Dict, Optional, Tuple


class ReflectorRanking:
    def __init__(self):
        self.reflector_available = self._check_reflector_availability()
    
    def _check_reflector_availability(self) -> bool:
        """Check if reflector is installed and available."""
        try:
            result = subprocess.run(['which', 'reflector'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Return whether reflector is available for use."""
        return self.reflector_available
    
    def rank_mirrors_with_reflector(self, 
                                  country: Optional[str] = None,
                                  protocol: Optional[str] = None,
                                  max_mirrors: int = 20,
                                  sort_by: str = "rate") -> List[Dict]:
        """
        Use reflector to rank mirrors effectively.
        
        Args:
            country: Country code (e.g., 'US', 'DE', 'GB')
            protocol: Protocol filter ('https', 'http')
            max_mirrors: Maximum number of mirrors to return
            sort_by: Sort criteria ('rate', 'score', 'delay', 'age')
        
        Returns:
            List of ranked mirror dictionaries
        """
        if not self.reflector_available:
            raise Exception("Reflector is not installed. Please install it with: sudo pacman -S reflector")
        
        try:
            # Build reflector command
            cmd = [
                'reflector',
                '--verbose',
                '--latest', '24',  # Only consider mirrors updated in last 24 hours
                '--completion-percent', '95',  # Only mirrors with 95%+ completion
                '--number', str(max_mirrors),
                '--sort', sort_by,
                '--save', '/dev/stdout'  # Output to stdout instead of file
            ]
            
            # Add country filter if specified
            if country and country != "All Countries":
                cmd.extend(['--country', country])
            
            # Add protocol filter if specified
            if protocol and protocol != "All":
                cmd.extend(['--protocol', protocol])
            
            # Run reflector
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"Reflector failed: {result.stderr}")
            
            # Parse the mirrorlist output
            mirrors = self._parse_reflector_output(result.stdout)
            
            return mirrors
            
        except subprocess.TimeoutExpired:
            raise Exception("Reflector operation timed out")
        except Exception as e:
            raise Exception(f"Reflector ranking failed: {str(e)}")
    
    def _parse_reflector_output(self, mirrorlist_content: str) -> List[Dict]:
        """Parse reflector's mirrorlist output into mirror dictionaries."""
        mirrors = []
        current_country = "Unknown"
        
        lines = mirrorlist_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and general comments
            if not line or line.startswith('##'):
                continue
            
            # Extract country from comment lines
            if line.startswith('#') and not line.startswith('# Server'):
                # Remove leading # and clean up
                country_line = line[1:].strip()
                if country_line and not any(x in country_line.lower() for x in ['server', 'generated', 'arch', 'repository']):
                    current_country = country_line
                continue
            
            # Parse server lines
            if line.startswith('Server = '):
                url = line[9:].strip()  # Remove "Server = "
                
                # Extract protocol
                if url.startswith('https://'):
                    protocol = 'https'
                elif url.startswith('http://'):
                    protocol = 'http'
                elif url.startswith('rsync://'):
                    protocol = 'rsync'
                else:
                    protocol = 'unknown'
                
                mirror = {
                    'url': url,
                    'country': current_country,
                    'protocol': protocol,
                    'rank': len(mirrors) + 1,  # Reflector already sorted them
                    'score': 100 - len(mirrors),  # Higher score for better rank
                    'source': 'reflector'
                }
                
                mirrors.append(mirror)
        
        return mirrors
    
    def get_fastest_mirrors_with_reflector(self, 
                                         country: Optional[str] = None,
                                         protocol: Optional[str] = None,
                                         max_mirrors: int = 10) -> List[Dict]:
        """Get the fastest mirrors using reflector's rate-based sorting."""
        return self.rank_mirrors_with_reflector(
            country=country,
            protocol=protocol,
            max_mirrors=max_mirrors,
            sort_by="rate"
        )
    
    def get_most_up_to_date_mirrors(self, 
                                   country: Optional[str] = None,
                                   protocol: Optional[str] = None,
                                   max_mirrors: int = 10) -> List[Dict]:
        """Get the most up-to-date mirrors using reflector's age-based sorting."""
        return self.rank_mirrors_with_reflector(
            country=country,
            protocol=protocol,
            max_mirrors=max_mirrors,
            sort_by="age"
        )
    
    def get_best_score_mirrors(self, 
                              country: Optional[str] = None,
                              protocol: Optional[str] = None,
                              max_mirrors: int = 10) -> List[Dict]:
        """Get the best overall mirrors using reflector's score-based sorting."""
        return self.rank_mirrors_with_reflector(
            country=country,
            protocol=protocol,
            max_mirrors=max_mirrors,
            sort_by="score"
        )
    
    def get_reflector_info(self) -> Dict:
        """Get information about reflector installation and capabilities."""
        if not self.reflector_available:
            return {
                'available': False,
                'version': None,
                'installation_command': 'sudo pacman -S reflector'
            }
        
        try:
            # Get reflector version
            result = subprocess.run(['reflector', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            version = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            return {
                'available': True,
                'version': version,
                'sort_options': ['rate', 'score', 'delay', 'age'],
                'features': [
                    'Mirror synchronization status',
                    'Completion percentage filtering',
                    'Multiple sorting criteria',
                    'Country and protocol filtering',
                    'Automatic mirror validation'
                ]
            }
        except Exception:
            return {
                'available': True,
                'version': "Unknown",
                'sort_options': ['rate', 'score', 'delay', 'age'],
                'features': ['Basic mirror ranking']
            }