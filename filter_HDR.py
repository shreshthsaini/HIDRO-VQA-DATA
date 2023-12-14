""" 
    Filtering the raw data videos based on the following criteria:
        1. HDR
        2. Resolution: 4K (3840x2160)
        3. Bitrate: 28 Mbps
        4. FPS: 50
        5. Bitrate per frame per pixel: 0.32

    Meta data:
        Resolution, 
        FPS,
        Codec,
        Bit depth,
        Bitrate,
        Duration,
        Size,
        Colorspace,
        Color transfer,
        Color primaries,
        Chroma location,

    -- Shreshth Saini
    -- September 2023
"""

from pathlib import Path
import os 
import json 
import subprocess 
import pandas as pd
import numpy as np
from tqdm import tqdm 
import argparse

#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Function to get metadata of a video using ffprobe.
"""
def get_metadata(video):
    
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_streams",
        "-select_streams", "v:0",
        "-print_format", "json",
        video
        ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    video_info = json.loads(result.stdout)
    video_stream = video_info["streams"][0]

    return video_stream

#--------------------------------------------------------------*****--------------------------------------------------------------#
"""
    Function to add metadata to dataframe.
"""

def add_metadata(df, video, video_stream,count):

    v_name = video.split('/')[-1]
    v_path = video
    width = video_stream["width"]
    height = video_stream["height"]
    
    # If resolution is not available, calculate from width and height
    if "display_aspect_ratio" not in video_stream:
        resolution = str(video_stream["width"]) + "x" + str(video_stream["height"])
    else:
        resolution = video_stream["display_aspect_ratio"]
    
    codec = video_stream["codec_name"]
    pix_fmt = video_stream["pix_fmt"]
    
    # If bit depth is not available, fill None 
    if "bits_per_raw_sample" not in video_stream:
        bit_depth = None
    else:
        bit_depth = video_stream["bits_per_raw_sample"]
    
    # If duration is not available, get from ffprobe show_entries      
    if "duration" not in video_stream:
        cmd_duration = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video
        ]
        result_duration = subprocess.run(cmd_duration, capture_output=True, text=True)
        duration = result_duration.stdout
    else:
        duration = video_stream["duration"]
    
    # If bitrate is not available, calculate from size and duration. Get the size from os 
    bitrate = (os.path.getsize(video)*8) / (float(result_duration.stdout)*1000000)
    
    # If size is not available, get it from os 
    if "size" not in video_stream:
        size = os.path.getsize(video)*8
    else:
        size = video_stream["size"]
    
    color_range = video_stream["color_range"]    
    colorspace = video_stream["color_space"]
    color_transfer = video_stream["color_transfer"]
    color_primaries = video_stream["color_primaries"]
    
    # If fps is not available, calculate from duration and nb_frames
    if "avg_frame_rate" not in video_stream:
        fps = video_stream["nb_frames"] / video_stream["duration"]     
    else:
        fps = video_stream["avg_frame_rate"]
    
    # adding all the metadata to dataframe
    df.loc[count] = [v_name, v_path, resolution, width, height, fps, codec, pix_fmt, bit_depth, bitrate, duration, size, colorspace, color_transfer, color_range, color_primaries]
    
    return df
    
#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Filter and save csv file with metadata of all videos.

"""

def filter_save(df, hdr_vids):

    # Split the fps column into two columns: num and dec and get the float value of fps. 
    df["fps_float"] = df["fps"].apply(lambda x: float(x.split("/")[0])/float(x.split("/")[1]))

    # Make new column with bitrate(in MBps)/(resolution*frame_rate) and then filter based on that.
    # Use MBps not bps
    df["bit_per_frame_per_pixel"] = (df["bitrate(Mbps)"])/(df["width"]*df["height"]*df["fps_float"])

    # filter HDR videos from numpy array
    hdr_files = np.load(hdr_vids)
    df = df[df["video_name"].isin(hdr_files)]

    # Save the HDR dataframe as csv file
    df.to_csv('HDR_vids_meta_data.csv', index=False)


    # Filtering the dataframe based on width and height, bitrate, duration, fps.    
    # Filter all 4k videos 
    df_filtered = df[(df["width"]==3840) & (df["height"]==2160)]

    # Diltering based on bitrate per frame per pixel from HDR LIVE dataset (average)
    threshold = 28/(3840*2160*60) #0.32

    df_filtered = df_filtered[(df_filtered["bit_per_frame_per_pixel"]>=threshold) & (df_filtered["fps_float"]>=50)]
    print("Final Assumed Pristine HDR 4K High FPS and High Bitrate Videos: ",len(df_filtered))

    #save the dataframe as csv file
    df_filtered.to_csv('HDR_meta_data_filtered_bfpHDRLIVE_4K_50fps.csv', index=False)

    return 


#--------------------------------------------------------------*****--------------------------------------------------------------#

def main(video_root, hdr_vids):
    # Read all the videos in the folder 
    vid_list = os.listdir(video_root ,hdr_vids)
    video_path = [video_root+"/"+v for v in vid_list if v.split('.')[-1] in ['mp4', 'mkv', 'mov', 'webm']]
    print(f"Total video count: {len(video_path)}")
    
    # save the metadata in panda dataframe
    df = pd.DataFrame(columns=['video_name', 'video_path', 'resolution', 'width', 'height', 'fps', 'codec', 'pix_fmt', 'bit_depth', 'bitrate(Mbps)', 'duration(s)', 'size(b)', 'colorspace', 'color_transfer', 'color_range', 'color_primaries']) 

    count = 0
    for v in tqdm(video_path):
        # print(f"Checking {v}...")
        try:
            video_stream = get_metadata(v)        
        except:
            print(f"{v} doesn't have metadata or correct container info!")
            continue
        # add metadata to dataframe 
        df = add_metadata(df, v, video_stream,count)
        count +=1

    # Filter and save the dataframe 
    filter_save(df, hdr_vids)

    return  

#--------------------------------------------------------------*****--------------------------------------------------------------#
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--video_root', type=str, required=True, help='Path to folder of videos')
    parser.add_argument('--hdr_vids', type=str, default="HDR_videos.npy", help='Path to HDR videos list')
    args = parser.parse_args()
    
    main(args.video_root, args.hdr_vids)
