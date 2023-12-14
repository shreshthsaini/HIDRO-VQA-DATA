""" 
    Ensure that your memory supports the number of jobs you are running in parallel else it will generate corrupted files.

    We clip the videos in an interval of 2min for 10sec clip; Re-encode the video with PQ (if original in HLG) and H.265 codec. Change the bitrate to 50 Mbps.

    NOTE: We did not use two-pass encoding since we are using CBR. 
    NOTE: We did not use extra metadata info for encoding with H.265, it increases the encoding time but gives better HDR10 encodings. We didn't see any significant difference.
    NOTE: make sure to keep the ffmpeg binary in the same folder as this script.

    -- Shreshth Saini, Sept. 2023

"""

import pandas as pd
import numpy as np
import os
from tqdm import tqdm
import subprocess
import json 
import argparse


#--------------------------------------------------------------*****--------------------------------------------------------------#
# Reading with video with ffprobe to get metadata 
def parse_probe_out(filename):

    # Get the fps 
    fps_cmnd = ['ffprobe', '-v', 'error', '-select_streams', 'v', '-of',
                'default=noprint_wrappers=1:nokey=1', '-show_entries', 'stream=r_frame_rate', filename]

    p = subprocess.Popen(fps_cmnd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    fps_out, err = p.communicate()
    fps_out = fps_out.decode()
    fps = eval(fps_out.split('\r')[0])

    # Get the metadata
    cmnd = ['ffprobe', '-show_streams', 
            '-print_format', 'json',
            filename]
    # ffprobe command to read the first frameformat (since HDR10, it's sufficient to read the first frame)
    # information about color_space,color_primaries,color_transfer,side_data_list,pix_fmt are extracted to the variable out
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    # Get dictionary of metadata 
    out = out.decode()
    info = json.loads(out)['streams'][0]
    if 'side_data_list' not in info:
        print(f"Warning: 'side_data_list' not found in metadata for {filename}.")

    try: 
        side_info = info['side_data_list'][-1]
        for k in side_info.keys():
            side_info[k] = side_info[k].split('/')[0]
    except: 
        print(f"Warning: 'Either side_data_list' not found or extraction error: {filename}.")
        print("Using default values side_data_list")
        side_info = {}
        side_info['green_x'] = "13248"
        side_info['green_y'] = "34500"
        side_info['blue_x'] = "7500"
        side_info['blue_y'] = "3000"
        side_info['red_x'] = "34000"
        side_info['red_y'] = "16000"
        side_info['white_point_x'] = "15634"
        side_info['white_point_y'] = "16450"
        side_info['max_luminance'] = "10000000"
        side_info['min_luminance'] = "50"

    return side_info, fps
        
     
#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Function to construct ffmpeg command for clipping and encoding the video.
"""
def construct_ffmpeg_command(input_file, output_file, color_tf, start_time, duration, bitrate, level=5.1):
    # See https://trac.ffmpeg.org/wiki/Encode/H.265 for more details
    
    # get metadata 
    side_info, fps = parse_probe_out(input_file)
    side_info['level'] = level
    side_info['keyint'] = int(2*fps)
    side_info['bitrate'] = bitrate
    side_info['bufsize'] = int(2*bitrate)

    # Add more color and metadata info for better encoding  
    x_265_paras_10bit = f'hdr-opt=1:repeat-headers=1:keyint={side_info["keyint"]}:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G({side_info["green_x"]},{side_info["green_y"]})B({side_info["blue_x"]},{side_info["blue_y"]})R({side_info["red_x"]},{side_info["red_y"]})WP({side_info["white_point_x"]},{side_info["white_point_y"]})L({side_info["max_luminance"]},{side_info["min_luminance"]}):max-cll=0,0:strict-cbr=1:level={side_info["level"]}:vbv-maxrate={side_info["bitrate"]}:vbv-bufsize={side_info["bufsize"]}:'
    # Add this to extend line : '-x265-params', x_265_paras_10bit, 
    
    # trying to split video at once into multipl clips 
    filters = ";".join([
        f"[0:v]trim={start}:{start + dur},setpts=PTS-STARTPTS[v{i}]" 
        for i, (start, dur) in enumerate(zip(start_time, duration))
    ])
    
    # Add more color and metadata info for better encoding  
    x_265_paras_10bit = f'hdr-opt=1:repeat-headers=1:keyint={side_info["keyint"]}:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G({side_info["green_x"]},{side_info["green_y"]})B({side_info["blue_x"]},{side_info["blue_y"]})R({side_info["red_x"]},{side_info["red_y"]})WP({side_info["white_point_x"]},{side_info["white_point_y"]})L({side_info["max_luminance"]},{side_info["min_luminance"]}):max-cll=0,0:strict-cbr=1:level={side_info["level"]}:vbv-maxrate={side_info["bitrate"]}:vbv-bufsize={side_info["bufsize"]}:'
    # Add this to extend line : '-x265-params', x_265_paras_10bit, 
        
    map_args = []
    for i, output in enumerate(output_file):
        if color_tf == "arib-std-b67":
            filters += f";[v{i}]zscale=transfer=smpte2084:transferin={color_tf}[outv{i}]"
            map_args.extend([f"-map", f"[outv{i}]", '-map_metadata', '0', "-c:v", "libx265", '-profile:v', 'main10', "-b:v", f"{side_info['bitrate']}k", "-minrate",f"{side_info['bitrate']}k", "-maxrate", f"{side_info['bitrate']}k", "-bufsize", f"{side_info['bufsize']}k", '-x265-params', x_265_paras_10bit, output]) #buf is 2 times of bitrate
        else:
            map_args.extend([f"-map", f"[v{i}]", '-map_metadata', '0', "-c:v", "libx265", '-profile:v', 'main10', "-b:v", f"{side_info['bitrate']}k", "-minrate", f"{side_info['bitrate']}k", "-maxrate", f"{side_info['bitrate']}k", "-bufsize", f"{side_info['bufsize']}k", '-x265-params', x_265_paras_10bit, output])

    cmd = [
        "./ffmpeg",
        "-i", input_file,
        "-filter_complex", filters,        
        *map_args
    ]

    return cmd


#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Function to extract clips from the video.
"""
def extract_clips(vid, start_times, color_tf, save_add, bitrate=50000): #bitrate in kbps
    durations = [10] * len(start_times)  # All clips are 10 seconds long
    output_files = [os.path.join(save_add, f"{os.path.basename(vid).split('.')[0]}_{ss}.mp4") for ss in start_times]

    ffmpeg_cmd = construct_ffmpeg_command(vid, output_files, color_tf, start_times,durations, bitrate)
    subprocess.run(ffmpeg_cmd)


#--------------------------------------------------------------*****--------------------------------------------------------------#
"""
    Main function
"""
def main(df,save_add):
    for _, row in tqdm(df.iterrows(), total=len(df)):
        # Skip clipping if aready clipped     
        #NOT IMPLEMENTED YET

        extract_clips(
            vid=row['video_path'], 
            start_times=[np.random.randint(st, st+120) for st in range(60, int(row['video_path'].split("_")[-1].split(".")[0])-130, 130)],
            color_tf=row['color_transfer'],
            save_add=save_add
        ) 

#--------------------------------------------------------------*****--------------------------------------------------------------#
if __name__ == "__main__":
    # Read the csv file
    df = pd.read_csv("./HDR_meta_data_filtered_bfpHDRLIVE_4K_50fps.csv")
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--save_add', type=str, default="./HDR_Clips/", help='Path to save the clips')
    args = parser.parse_args()

    # Create the folder if it doesn't exist 
    if not os.path.exists(args.save_add):
        os.makedirs(args.save_add)
    
    main(df,args.save_add)


