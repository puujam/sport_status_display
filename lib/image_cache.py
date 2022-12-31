import os
import requests
import threading

from PySide6 import QtCore, QtWidgets, QtGui

lib_dir = os.path.dirname(os.path.realpath(__file__))
image_cache_directory = os.path.realpath(os.path.join(lib_dir, "..", "cache"))

if not os.path.isdir(image_cache_directory):
    os.makedirs(image_cache_directory)

def get_image_and_assign_work(team, logo_layout):
    image_url = team.logo_dark

    image_name = os.path.basename(image_url)
    league_name = image_url.split("/")[-4]


    local_league_path = os.path.join(image_cache_directory, league_name)
    local_image_path = os.path.join(local_league_path, image_name)

    if not os.path.isdir(local_league_path):
        os.makedirs(local_league_path)
    
    if not os.path.isfile(local_image_path):
        image_data = requests.get(image_url).content
        with open(local_image_path, "wb") as file_handle:
            file_handle.write(image_data)
    
    logo_layout.local_image_path = local_image_path
    logo_layout.update_image()

def get_image_and_assign(team, logo_layout):
    work_thread = threading.Thread(target=get_image_and_assign_work, args=[team, logo_layout])
    work_thread.start()