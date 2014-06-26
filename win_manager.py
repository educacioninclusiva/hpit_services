import argparse
import json
import subprocess
import os
import time
import signal
import shlex
import sys 

from base_manager import BaseManager

DETACHED_PROCESS = 8 #code for windows subprocess

class WindowsManager(BaseManager):

    def spin_up_all(self, entity_type, configuration):
        """
        Start all entities of a given type, as specified in configuration
        """
        
        entity_collection = self.get_entity_collection(entity_type, configuration)
        
        for item in entity_collection:
            if not item['active']:
                item['active'] = True
                name = item['name']
                entity_subtype = item['type']
                entity_id = item['entity_id']
                api_key = item['api_key']
                
                print("Starting entity: " + name)
                pidfile = self.get_entity_pid_file(entity_type, name)
                
                subp_args = [sys.executable, "entity_daemon.py", "--pid", pidfile]
                
                if 'args' in item:
                    entity_args = shlex.quote(json.dumps(item['args']))
                    subp_args.append("--args")
                    subp_args.append(entity_args)
                    
                if 'once' in item:
                    subp_args.append("--once")
                    
                subp_args.extend([entity_id, api_key, entity_type, entity_subtype])
                
                if entity_type != 'tutor' and entity_type !='plugin':
                    raise Exception("Error: unknown entity type in spin_up_all")
                
                with open("tmp/output_"+entity_type+"_"+entity_subtype+".txt","w") as f:
                    subp = subprocess.Popen(subp_args, creationflags=DETACHED_PROCESS, stdout = f, stderr = f)
                with open(pidfile,"w") as pfile:
                    pfile.write(str(subp.pid))
                    
                        

    def wind_down_collection(self, entity_type, entity_collection):
        """
        Shut down all entities of a given type from a collection
        """
        
        for item in entity_collection:
            if item['active']:
                item['active'] = False
                name = item['name']
                print("Stopping entity: " + name)
                pidfile = self.get_entity_pid_file(entity_type, name)

                try:
                    with open(pidfile) as f:
                        pid = f.read()
                        os.kill(int(pid), signal.SIGTERM)

                    os.remove(pidfile)
                except FileNotFoundError:
                    print("Error: Could not find PIDfile for entity: " + name)


    def start(self, arguments, configuration):
        """
        Start the hpit server, tutors, and plugins as specified in configuration
        """
        
        if not os.path.exists('tmp'):
            os.makedirs('tmp')

        if not os.path.exists('log'):
            os.makedirs('log')

        if self.server_is_running():
            print("The HPIT Server is already running.")
        else:
            print("Starting the HPIT Hub Server for Windows...")
            with open("tmp/output_server.txt","w") as f:
                subp = subprocess.Popen([sys.executable, "server_wrapper.py", "--pid", self.settings.HPIT_PID_FILE], creationflags=DETACHED_PROCESS, stdout = f, stderr = f)
            with open(self.settings.HPIT_PID_FILE,"w") as pfile:
                pfile.write(str(subp.pid))

            print("Waiting for the server to boot.")
            time.sleep(5)

            print("Starting tutors...")
            self.spin_up_all('tutor', configuration)
            print("Starting plugins...")
            self.spin_up_all('plugin', configuration)
        print("DONE!")


    def stop(self, arguments, configuration):
        """
        Stop the hpit server, plugins, and tutors.
        """
        
        if self.server_is_running():
            print("Stopping plugins...")
            self.wind_down_all('plugin', configuration)
            print("Stopping tutors...")
            self.wind_down_all('tutor', configuration)

            print("Stopping the HPIT Hub Server...")
            with open(self.settings.HPIT_PID_FILE) as f:
                pid = f.read()
                os.kill(int(pid), signal.SIGTERM)
            os.remove(self.settings.HPIT_PID_FILE)
        else:
            print("The HPIT Server is not running.")
        print("DONE!")
