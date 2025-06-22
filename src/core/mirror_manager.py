import requests


class MirrorManager:
    MIRRORLIST_URL = "https://archlinux.org/mirrorlist/"

    def fetch_mirrors(self, country=None, protocol=None, active_only=True):
        params = {
            'use_mirror_status': 'on'
        }
        if country:
            params['country'] = country
        if protocol:
            params['protocol'] = protocol
        if active_only:
            params['use_mirror_status'] = 'on'

        print(f"Fetching mirrors from: {self.MIRRORLIST_URL}")
        print(f"Parameters: {params}")
        
        try:
            response = requests.get(self.MIRRORLIST_URL, params=params, timeout=10)
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                mirrors = self.parse_mirrors(response.text)
                print(f"Parsed {len(mirrors)} mirrors")
                return mirrors
            else:
                raise Exception(f"Failed to fetch mirror list. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {str(e)}")

    def parse_mirrors(self, mirrorlist_text):
        mirrors = []
        current_country = "Unknown"
        
        for line in mirrorlist_text.splitlines():
            line = line.strip()
            if not line:
                continue
            
            # Extract country from comments (format: ## Country Name)
            if line.startswith('##') and len(line) > 3:
                # Skip header comments that contain "Arch Linux" or "Generated"
                if 'Arch Linux' not in line and 'Generated' not in line and 'Filtered' not in line:
                    potential_country = line[2:].strip()  # Remove ## and whitespace
                    if potential_country and not potential_country.startswith('http'):
                        current_country = potential_country
                continue
            
            # Parse mirror URLs
            if line.startswith('#Server = ') or line.startswith('Server = '):
                url = line.replace('#Server = ', '').replace('Server = ', '')
                
                # Determine protocol
                if url.startswith('https://'):
                    protocol = 'https'
                elif url.startswith('http://'):
                    protocol = 'http'
                elif url.startswith('rsync://'):
                    protocol = 'rsync'
                else:
                    protocol = 'unknown'
                
                mirrors.append({
                    'protocol': protocol,
                    'url': url,
                    'country': current_country
                })
        
        return mirrors
