import subprocess
import time


def test_mirror_speed(url, timeout=15):
    """
    Test mirror speed by downloading a small file and measuring the speed.
    Returns speed in bytes per second or None if failed.
    """
    try:
        # Replace template variables with actual values
        test_url = url.replace('$repo', 'core').replace('$arch', 'x86_64')
        
        # Ensure the URL ends with the database file
        if not test_url.endswith('core.db'):
            # Remove trailing slash if present
            test_url = test_url.rstrip('/')
            # Add the database file name
            test_url += '/core.db'
        
        print(f"Testing speed for: {test_url} (timeout: {timeout}s)")
        
        # First attempt: Standard speed test
        result = _curl_speed_test(test_url, timeout, standard=True)
        
        if result is not None:
            return result
        
        # Second attempt: Fallback with different settings
        print(f"Retrying with fallback settings: {test_url}")
        return _curl_speed_test(test_url, timeout, standard=False)
            
    except subprocess.TimeoutExpired:
        print(f"Timeout testing mirror: {url}")
        return None
    except Exception as e:
        print(f"Error testing mirror speed for {url}: {e}")
        return None


def _curl_speed_test(test_url, timeout, standard=True):
    """
    Internal function to perform curl speed test with different configurations.
    """
    try:
        if standard:
            # Standard configuration
            cmd = [
                "curl", 
                "-o", "/dev/null",  # Don't save the file
                "-s",               # Silent mode
                "-L",               # Follow redirects
                "-f",               # Fail silently on HTTP errors
                "-w", "%{speed_download}",  # Output only the speed
                "--max-time", str(timeout), # Timeout
                "--connect-timeout", "5",   # Connection timeout
                "--retry", "1",     # Retry once on failure
                "--retry-delay", "1", # Wait 1 second between retries
                "--user-agent", "PKOS-Mirrorlist-Manager/2.0", # Identify our app
                test_url
            ]
        else:
            # Fallback configuration - more aggressive settings
            cmd = [
                "curl", 
                "-o", "/dev/null",  # Don't save the file
                "-s",               # Silent mode
                "-L",               # Follow redirects
                "-w", "%{speed_download}",  # Output only the speed
                "--max-time", str(timeout + 5), # Longer timeout
                "--connect-timeout", "8",   # Longer connection timeout
                "--retry", "2",     # More retries
                "--retry-delay", "2", # Longer delay between retries
                "--user-agent", "Mozilla/5.0 (compatible; PKOS-Mirrorlist-Manager)", # Different user agent
                "--compressed",     # Accept compressed responses
                test_url
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
        
        if result.returncode == 0 and result.stdout.strip():
            try:
                speed = float(result.stdout.strip())
                return speed if speed > 0 else None
            except ValueError:
                print(f"Invalid speed value returned: {result.stdout.strip()}")
                return None
        else:
            # Map common curl error codes to user-friendly messages
            error_codes = {
                6: "Couldn't resolve host",
                7: "Failed to connect to host",
                28: "Operation timeout",
                22: "HTTP error (404, 403, etc.)",
                35: "SSL connect error",
                56: "Failure receiving network data"
            }
            
            error_msg = error_codes.get(result.returncode, f"Curl error {result.returncode}")
            if result.stderr and not standard:  # Only show detailed errors on fallback
                error_msg += f": {result.stderr.strip()}"
            
            if not standard:  # Only print error on final attempt
                print(f"Mirror test failed - {error_msg}")
            return None
            
    except subprocess.TimeoutExpired:
        if not standard:
            print(f"Timeout on fallback attempt")
        return None
    except Exception as e:
        if not standard:
            print(f"Error in fallback test: {e}")
        return None


def ping_mirror(url, count=3):
    """
    Ping a mirror to test connectivity.
    Returns average ping time in ms or None if failed.
    """
    try:
        # Extract hostname from URL
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return None
            
        result = subprocess.run([
            "ping", "-c", str(count), "-W", "3", hostname
        ], capture_output=True, text=True, timeout=15)
        
        if result.returncode == 0:
            # Parse ping output to get average time
            lines = result.stdout.split('\n')
            for line in lines:
                if 'avg' in line and 'min/avg/max' in line:
                    # Extract average from: min/avg/max/mdev = 1.234/5.678/9.012/1.234 ms
                    parts = line.split('=')[1].strip().split('/')
                    if len(parts) >= 2:
                        return float(parts[1])
        return None
        
    except Exception as e:
        print(f"Error pinging {url}: {e}")
        return None
