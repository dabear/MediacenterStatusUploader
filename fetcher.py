# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""
import requests
import http.cookiejar as cookiejar
import xml.etree.ElementTree as ET
import json
from collections import Counter

import socket

from deluge_web_client import DelugeWebClient
import logging, sys

import time, os
from plexapi.myplex import MyPlexAccount

#requirements:
    #pip install deluge-web-client
    #pip install plexapi
    
#python spyder version:
    #/Users/bjorninge/Library/spyder-6/envs/spyder-runtime/bin/python
class Checker:
    host = "http://192.168.10.110"
    JACKETT_HOST = os.getenv("JACKETT_HOST", "http://192.168.10.110:9117")
    JACKETT_KEY = os.getenv("JACKETT_KEY", "")
    JACKETT_MIN_TRACKERS = 2
    JACKETT_MIN_ITEMS_PER_TRACER = 5

    SONARR_BASE_URL = os.getenv("SONARR_BASE_URL", "http://192.168.10.110:8989/")
    SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")

    RADARR_BASE_URL = os.getenv("RADARR_BASE_URL", "http://192.168.10.110:7878/")
    RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")

    DELUGE_URL = os.getenv("DELUGE_URL", "http://192.168.10.110:8112/")
    DELUGE_PASSWORD = os.getenv("DELUGE_PASSWORD", "")

    PLEX_SERVER = os.getenv("PLEX_SERVER", "")  # Optionally set this or leave it empty
    PLEX_USERNAME = os.getenv("PLEX_USERNAME", "")
    PLEX_PASSWORD = os.getenv("PLEX_PASSWORD", "")

    disk_percentage_threshold = int(os.getenv("DISK_PERCENTAGE_THRESHOLD", 25))
    
    # Path to the temporary cookie file
    cookie_file = "temp_cookies.txt"
    
    
    remote_status_receiver = os.getenv("REMOTE_STATUS_RECEIVER", "")
    

    check_jackett = os.getenv("CHECK_JACKETT", "true").lower() == "true"
    check_sonarr = os.getenv("CHECK_SONARR", "true").lower() == "true"
    check_deluge = os.getenv("CHECK_DELUGE", "true").lower() == "true"
    check_plex = os.getenv("CHECK_PLEX", "true").lower() == "true"
    check_radarr = os.getenv("CHECK_RADARR", "true").lower() == "true"
    
    class ServiceStatusException(Exception):
        """Base exception for all service status errors."""
        def __init__(self, message):
            super().__init__(message)
    
    class JackettStatusException(ServiceStatusException):
        pass

    class SonarrStatusException(ServiceStatusException):
        pass

    class DelugeStatusException(ServiceStatusException):
        pass

    class RadarrStatusException(ServiceStatusException):
        pass

    class PlexStatusException(ServiceStatusException):
        pass
    

    def __init__(self):
        # Create a session
        self.session = requests.Session()
        # Load cookies from the file into the session
        self.cookie_jar = cookiejar.MozillaCookieJar(self.cookie_file)
        
        # Load cookies from the file into the session
        try:
            # Load cookies from the file
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
            self.session.cookies.update(self.cookie_jar)
            print("Cookies loaded from file.")
        except FileNotFoundError:
            print("Cookie file not found. Starting with no cookies.")
            
        self.setup_logging()
            
            
    def createStatus(self, program, subcomponent, status):
        if isinstance(status, Exception):
            status = str(status)  # Convert Exception to string for JSON serialization
        return {"program": program, "subcomponent": subcomponent, "status": status}
            
            
    def _check_all(self):
        
        grouped_checks = { 
            "jackett": [self.jackett_check_indexers_status] if self.check_jackett else [],
            "sonarr": [
                self.sonarr_check_ping, 
                self.sonarr_check_health,
                self.sonarr_check_disk_status
            ] if self.check_sonarr else [],
            "deluge": [
                self.deluge_check_connection
                ] if self.check_deluge else [],
            "plex": [
                self.plex_check_connection
                ] if self.check_plex else [],
            "radarr": [
                self.radarr_check_ping,
                self.radarr_check_health,
                self.radarr_check_disk_status
                ] if self.check_radarr else []
            
        }
        
        statuses = []
        
        for group, fns in grouped_checks.items():
            if not fns:
                continue
            for fn in fns:
                component_name = fn.__name__
                print(f"got function {component_name} for group {group}")
                try:
                    statuses.append(self.createStatus(group, component_name, fn() or "uknown" ) )
                except Exception as e:
                    statuses.append(self.createStatus(group, component_name, e ))
                    
        print(f"all checks: {json.dumps(statuses)}")
        return statuses
    
    def check_and_upload_status(self):
        logging.debug("checking all statuses, aiming at uploading them")
        statuses = self._check_all()
        
        alen = len(statuses)
        if alen:
            logging.debug(f"uploading {alen} statuses")
            try:
                self._upload_statuses(statuses)
            except Exception as e:
                print(f"got exception uploading: {e}")
        else:
            print("Error: No checks enabled, not uploading")
        
    def _upload_statuses(self, statuses):
        
        
        _ = self.session.post(self.remote_status_receiver, headers={"Content-Type": "application/json"}, data=json.dumps(statuses))

    def setup_logging(self):
        # Configure basic logging
        logging.basicConfig(
            level=logging.DEBUG,  # Set the default logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),  # Logs to console
                logging.FileHandler("app.log", mode="a")  # Logs to a file (app.log)
            ]
        )
        _ = logging.getLogger(__name__)
    
    
    def deluge_check_connection(self):
        try:
            client = DelugeWebClient(url=self.DELUGE_URL, password=self.DELUGE_PASSWORD)
            client.login(timeout=10)
            host = client.get_hosts(timeout=5).result[0][0]
            
            status = client.get_host_status(host, timeout=5).result[1]
        
            
        except Exception as e:
            raise self.DelugeStatusException(f"Error checking deluge connection: {e}")
            return
    
            
        if status == "Connected":
            return "ok"
        
        raise self.DelugeStatusException(f"Deluge status was not Connected: {status}")
            
    #https://sonarr.tv/docs/api/
    def sonarr_check_health(self):
        url = f"{self.SONARR_BASE_URL}/api/v3/health?apikey={self.SONARR_API_KEY}"
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                raise self.SonarrStatusException(f"Could not check health. Response: {response.text}")
            
            issues = response.json()
            errors = [error for error in issues if error.get("type") == "error"]
            
            if len(errors) == 0:
                return "ok
            
            raise self.SonarrStatusException(f"Sonarr health errors: {problems}")
                
                
        except Exception as e:
            raise self.SonarrStatusException(f"Error during sonarr_check_health: {e}")
            
        return "ok"
    
    def sonarr_check_disk_status(self):
        url = f"{self.SONARR_BASE_URL}/api/v3/diskspace?apikey={self.SONARR_API_KEY}"
        

        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                disk_status = response.json()
                for disk in disk_status:
                    percentage_free = disk['freeSpace'] / disk['totalSpace'] * 100
                    if percentage_free < self.disk_percentage_threshold:
                        raise self.SonarrStatusException(f"percentage free was less than {self.disk_percentage_threshold} for path \"{disk['path']}\"")
                    #print(f"Path: {disk['path']}, Free Space: {disk['freeSpace'] / (1024**3):.2f} GB, Total Space: {disk['totalSpace'] / (1024**3):.2f} GB, free: {percentage_free:.2f}%")
            else:
                raise self.SonarrStatusException(f"Disk status request failed. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            raise self.SonarrStatusException(f"Error during disk status request: {e}")
        
        print("sonarr_check_disk_status check successful")
        return "ok"
            

    def sonarr_check_ping(self):
        url = f"{self.SONARR_BASE_URL}ping?apikey={self.SONARR_API_KEY}"
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get("status") == "OK":
                    print("sonarr_check_ping check successful")
                    return "ok"
                else:
                    raise self.SonarrStatusException(f"Ping json response failed. Response: {response.text}")
            else:
                raise self.SonarrStatusException(f"Ping failed. Status code: {response.status_code}, Response: {response.text}")
        except requests.RequestException as e:
            raise self.SonarrStatusException(f"Error during ping request: {e}")
    
    def radarr_check_disk_status(self):
        url = f"{self.RADARR_BASE_URL}/api/v3/diskspace?apikey={self.RADARR_API_KEY}"
        

        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                disk_status = response.json()
                for disk in disk_status:
                    percentage_free = disk['freeSpace'] / disk['totalSpace'] * 100
                    if percentage_free < self.disk_percentage_threshold:
                        raise self.RadarrStatusException(f"percentage free was less than {self.disk_percentage_threshold} for path \"{disk['path']}\"")
                    #print(f"Path: {disk['path']}, Free Space: {disk['freeSpace'] / (1024**3):.2f} GB, Total Space: {disk['totalSpace'] / (1024**3):.2f} GB, free: {percentage_free:.2f}%")
            else:
                raise self.RadarrStatusException(f"Disk status request failed. Status code: {response.status_code}, Response: {response.text}")
        except Exception as e:
            raise self.RadarrStatusException(f"Error during disk status request: {e}")
        
        print("radarr_check_disk_status check successful")
        return "ok"

    def radarr_check_ping(self):
        url = f"{self.RADARR_BASE_URL}ping?apikey={self.RADARR_API_KEY}"
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code == 200:
                response_json = response.json()
                if response_json.get("status") == "OK":
                    print("sonarr_check_ping check successful")
                    return "ok"
                else:
                    raise self.RadarrStatusException(f"Ping json response failed. Response: {response.text}")
            else:
                raise self.RadarrStatusException(f"Ping failed. Status code: {response.status_code}, Response: {response.text}")
        except requests.RequestException as e:
            raise self.RadarrStatusException(f"Error during ping request: {e}")

    def radarr_check_health(self):
        url = f"{self.RADARR_BASE_URL}/api/v3/health?apikey={self.RADARR_API_KEY}"
        try:
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                raise self.RadarrStatusException(f"Could not check health. Response: {response.text}")
            
            issues = response.json()
            errors = [error for error in issues if error.get("type") == "error"]

            if len(errors) == 0:
                return "ok"
            
            raise self.RadarrStatusException(f"Radarr health errors: {problems}")
                
                
        except Exception as e:
            raise self.RadarrStatusException(f"Error during radarr_check_health: {e}")
            
        return "ok"
    
    def jackett_check_indexers_status(self, i=2)->str:
             
        # Due to weirdness and cookie issues, 
        # jackett always needs two attempts if cookies file is empty
        if i == 0:
            return

        url = f"{self.JACKETT_HOST}/api/v2.0/indexers/all/results/torznab?apikey={self.JACKETT_KEY}"
        
        try:
            response = self.session.get(url, timeout=5)
            if response.status_code == 200:
                print("response retrieved")

                # Parse the XML data
                root = ET.fromstring(response.text)
                
                # Find all 'jackettindexer' tags
                jackettindexers = root.findall('.//jackettindexer')

                # Print the found tags
                counted = Counter([indexer.attrib['id'] for indexer in jackettindexers])
                
                tracker_count = 0
                for tracker, item_count in counted.items():
                    tracker_count +=1
                    if item_count < self.JACKETT_MIN_ITEMS_PER_TRACER:
                        raise self.JackettStatusException(f"jackett did not return enough indexer items for tracker: {tracker}")
 
                if tracker_count < self.JACKETT_MIN_TRACKERS:
                    raise self.JackettStatusException("jackett did not return enough trackers")
                    
                return "ok"
                
            else:
                raise self.JackettStatusException(f"Failed to fetch indexers. Status Code: {response.status_code}")
        except self.JackettStatusException:
            raise
        except Exception as e:
            print(f"Error checking indexers: {e}, response: ")
            i -= 1
            self.jackett_check_indexers_status(i)

    def plex_check_connection(self):
        try:
            account = MyPlexAccount(self.PLEX_USERNAME, self.PLEX_PASSWORD)
            #print(f"all servers: { account.resources()}")
            if self.PLEX_SERVER:
                plex = account.resource(self.PLEX_SERVER).connect() 
            else:
                # we connect to the first server
                plex = account.resources()[0].connect()
        except Exception as e:
            raise self.PlexStatusException(f"Error getting plex server for account {self.PLEX_USERNAME}")
        
        update_avail = False if plex.checkForUpdate() == None else True
        
        if update_avail:
            raise self.PlexStatusException("outdated plex detected")
        return "ok"
        



def main():
    print("yo")
    checker = Checker()
    checker.check_and_upload_status()

if __name__ == "__main__":
    main()
