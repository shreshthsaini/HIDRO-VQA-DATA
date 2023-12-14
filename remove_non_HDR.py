""" 
From the SantaFe dataset, remove/separate all non-HDR videos and save list of HDR videos and non-HDR videos. 

-- September 2023, Shreshth Saini 

"""

import os 
import subprocess 
import json 
from pathlib import Path 
import numpy as np
import pandas as pd
from tqdm import tqdm 
import argparse

#--------------------------------------------------------------*****--------------------------------------------------------------#

"""
 Core function to check if a video is HDR or not. 
 Use ffprobe to get video stream information in JSON format. 
 Check for Color Transfer, Color Space, and Bits per Raw Sample.
"""
def is_video_hdr(video_path):
    """
    Check if the video at the given path is HDR.

    Args:
    - video_path (str): The path to the video file.

    Returns:
    - bool: True if the video is HDR, False otherwise.
    """
    cmd = [
    "ffprobe", 
    "-v", "error", 
    "-show_streams",
    "-select_streams", "v:0",
    "-print_format", "json",
    video_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    #import pdb; pdb.set_trace()
    
    video_info = json.loads(result.stdout)

    video_stream = video_info["streams"][0]

    # Checking some common HDR indicators in the metadata
    # This can be extended based on more specific requirements
    if ("color_transfer" in video_stream and video_stream["color_transfer"] == "smpte2084") or \
        ("color_space" in video_stream and video_stream["color_space"] in ["bt2020nc", "bt2020c"]) or \
        ("bits_per_raw_sample" in video_stream and int(video_stream["bits_per_raw_sample"]) > 8):
        return True

    return False

#--------------------------------------------------------------*****--------------------------------------------------------------#

"""
 Main function to check for True HDR videos in a folder of videos.
"""
def main(video_path):
    
    # List of non-HDR videos
    non_HDR_videos = []
    # List of HDR videos  
    HDR_videos = []
    
    # List of all videos
    all_videos = os.listdir(video_path)
    
    # Loop through all videos
    for video in tqdm(all_videos):
        #check if video is HDR
        if is_video_hdr(video_path/video):
            HDR_videos.append(video)
        else:
            non_HDR_videos.append(video)

    # Save list of non-HDR videos
    np.save('non_HDR_videos.npy', non_HDR_videos)
    # Save list of HDR videos
    np.save('HDR_videos.npy', HDR_videos)
    # Print number of non-HDR videos
    print(len(non_HDR_videos))
    # Print number of HDR videos
    print(len(HDR_videos))

#--------------------------------------------------------------*****--------------------------------------------------------------#
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_path', type=str, required=True, help='Path to folder of videos')
    args = parser.parse_args()
    # Path to folder of videos
    video_path = Path(args.video_path)
    main(video_path)



