""" 
Distortion Generation for HDR Quality Aware Pre-Training :

Bit Ladder: 
* 4K - 3, 6, 15 Mbps
* 1080p - 1, 6, 9 Mbps
* 720p - 2.6, 4.6  Mbps
* 540p -  2.2 Mbps


Input videos are PQ 4K and ~50 Mbps with H.265 encoded. Make sure to use profile as main10/leve5.1 since we are using 10 bit videos.

We will compress each video to generate the distortions/ladder as mentioned above. 
We are using ffmpeg for this task using CBR since we are fixing the bitrate. 

# Two-pass encoding not used.
# You can either choose to use hdr-opt method to better encode the HDR10 video or use the default method as it increases the encoding time.

-- Shreshth Saini, Sept. 2023

"""
import os 
import glob 
import pandas as pd 
import numpy as np 
import json
import subprocess
import argparse

#--------------------------------------------------------------*****--------------------------------------------------------------#
# Default master display values for HDR10 
def default_display_dict():
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
    return side_info

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

    # skip

    # Get the metadata
    cmnd = ['ffprobe', '-hide_banner', '-probesize', '100', '-select_streams', 'v',
            '-print_format', 'json', '-read_intervals', '%+#300', '-show_frames', '-loglevel', 'warning',
            '-show_entries', 'frame=color_space,color_primaries,color_transfer,side_data_list,pix_fmt', filename]
    # ffprobe command to read the first frameformat (since HDR10, it's sufficient to read the first frame)
    # information about color_space,color_primaries,color_transfer,side_data_list,pix_fmt are extracted to the variable out
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()

    # Get dictionary of metadata 
    out = out.decode()
    info = json.loads(out)['frames'][0]
    
    if 'side_data_list' not in info:
        if False:
            print(f"Warning: 'side_data_list' not found in metadata for {filename}.")
            original_vid =  '/home/shreshth/HDD/SantaFe/Dataset/10k_word_10_20_mins/'+'_'.join(filename.split('/')[-1].split('_')[:-1])+'.webm'
            print(f"Obtaining the side_data_list from original video {original_vid}")
            # get the side_data_list from the original video in one command 
            orig_cmd = ['ffprobe',
                        '-i', original_vid,
                        '-show_streams', '-show_format', 
                        '-print_format', 'json']
            p = subprocess.Popen(orig_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = p.communicate()
            out = out.decode()
            info = json.loads(out)['streams'][0]
            side_info = info['side_data_list'][-1]
            
        else: 
            print(f"Warning: side_data_list extraction error: {filename}.")
            print("Using default values for side_info")
            side_info = default_display_dict()

    else:
        side_info = info['side_data_list'][-1]
        try: 
            for k in side_info.keys():
                side_info[k] = side_info[k].split('/')[0]
        except:
            print(f"Warning: side_data_list extraction error: {filename}.")
            print("Using default values for side_info")
            side_info = default_display_dict()
        # check all the keys are present else use default values 
        for k in default_display_dict().keys():
            if k not in side_info.keys():
                side_info[k] = default_display_dict()[k]
    
    return side_info, fps


#--------------------------------------------------------------*****--------------------------------------------------------------#
# Compression function. Fixed bitrate and scaling resolution, 
def compress_vid(filename, save_add, ladder, level=5.1):

    # Get the metadata and add input data in the metadata
    side_info, fps = parse_probe_out(filename)

    # Prepare the ffmpeg command for multiple outputs 
    cmd = ['./ffmpeg' , '-i', filename]

    for name, values in ladder.items():
        # getting the values from the ladder dict
        bitrate, width, height = values
        outname = os.path.join(save_add, name + "#" + filename.split("/")[-1])

        side_info['outname'] = outname 
        side_info['bitrate'] = int(bitrate*1000) #in kbps
        side_info['bufsize'] = int(bitrate*2*1000) #in kbps
        side_info['level'] = level
        side_info['keyint'] = int(2*fps)
        side_info['w'] = width
        side_info['h'] = height

        # extending the cmd, either set the bitrate, max, and min-bitrate seperatel or in -x265-params with vbv-maxrate, vbv-bufsize
        cmd.extend([
            '-vf', f'scale={width}:{height}', '-an', '-map', '0', '-c:v', 'libx265', '-profile:v', 'main10',
            '-b:v', f'{side_info["bitrate"]}k',
            '-map_metadata', '0',
            '-x265-params', f'hdr-opt=1:repeat-headers=1:keyint={side_info["keyint"]}:colorprim=bt2020:transfer=smpte2084:colormatrix=bt2020nc:master-display=G({side_info["green_x"]},{side_info["green_y"]})B({side_info["blue_x"]},{side_info["blue_y"]})R({side_info["red_x"]},{side_info["red_y"]})WP({side_info["white_point_x"]},{side_info["white_point_y"]})L({side_info["max_luminance"]},{side_info["min_luminance"]}):max-cll=0,0:strict-cbr=1:level={side_info["level"]}:vbv-maxrate={side_info["bitrate"]}:vbv-bufsize={side_info["bufsize"]}:',
            '-preset', 'slow', '-pix_fmt', 'yuv420p10le', 
            outname
        ])

    try:
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(e.returncode)
        print(e.output)
    
#--------------------------------------------------------------*****--------------------------------------------------------------#
def main(bit_ladder_csv, video_folder, save_add):
    # Reading the bitladder csv. First row is 60Mbps ref conversion which we can skip, since we already have 50Mbps videos. 
    bitladder = pd.read_csv(bit_ladder_csv).drop(0)
    # Get the ladder as dict : {name: [bitrate1, w, h]}
    print(bitladder.head())
    ladder = {}
    for i, row in bitladder.iterrows():
        ladder[row['name']] = [row['bitrate'],row['w'], row['h']]

    # Read all reference videos from folder 
    vids = glob.glob(video_folder + "*.mp4")

    # Try to make the folder if it doesn't exist 
    try:
        os.mkdir(save_add)
    except:
        print("Compression folder already exists")
    # Existing videos in the save address
    existing = [i.split("#")[-1] for i in os.listdir(save_add)]

    # Compress only if the video is not already compressed. Check with id of the video and not the name.
    for vid in vids:
        if vid.split('/')[-1] not in existing:
            # Compress the video 
            compress_vid(vid, save_add, ladder)
        else:
            print(f"{vid} already compressed")

#--------------------------------------------------------------*****--------------------------------------------------------------#
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bit_ladder_csv', type=str, required=True, help='Path to bit ladder csv')
    parser.add_argument('--video_folder', type=str, default="./HDR_Clips/", help='Path to folder of videos')
    parser.add_argument('--save_add', type=str, default="./HDR_Clips_BitLadder/", help='Path to save the compressed videos')
    args = parser.parse_args()

    bit_ladder_csv = "bitladder.csv" 
    main(args.bit_ladder_csv, args.video_folder, args.save_add)
