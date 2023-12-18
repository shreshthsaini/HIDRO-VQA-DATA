""" 
    In HIDRO-VQA workshop paper, we only trained the main network with 1 frame from each scene separated clip. 
    Mainly due to limited computational resources and scope of the paper.
    
    Extension: 
                However, in this code, you can extract n-frames from each clips and possibly create a bigger dataset. 

    - Shreshth Saini, 2023
"""

import numpy as np
import json
import os
import argparse
from glob import glob
import subprocess
import time
import argparse
import random

#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Helper function to read 10-bit video frames using FFmpeg

    NOTE: Structure is same as read_hdr_10bit.read_mp4_10bit(), except here we convert the frames to RGB format.
"""

def read_mp4_10bit(video_path, range='tv'):

    # Get video metadata
    command_probe = [
        "../HDR_Clips/ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,pix_fmt",
        "-of", "json",
        video_path
    ]
    
    result = subprocess.run(command_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    video_info = json.loads(result.stdout)
    video_stream = video_info['streams'][0]
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    
    # Set FFmpeg codec parameters for 10-bit video
    pix_fmt = video_stream.get('pix_fmt', 'yuv420p10le') # Adjust as necessary based on your video's pixel format

    # Define the scaling factors based on the range type
    if range == 'tv':
        offset = 64
        scale = 1 / (940 - 64)
    else:  # full range
        offset = 0
        scale = 1 / (1023 - 0)
    

    """ 
    Read video frames and convert them to a NumPy array
    """ 

    # Determine bytes per pixel based on the pixel format
    # Determine bytes per pixel and bit depth based on the pixel format
    if pix_fmt in ['yuv420p', 'yuvj420p']:
        bytes_per_pixel = 1.5
        bit_depth = 8
    elif pix_fmt in ['yuv420p10le', 'yuv420p10be']:
        bytes_per_pixel = 3
        bit_depth = 10
    elif pix_fmt in ['rgb48le', 'rgb48be']:
        bytes_per_pixel = 6
        bit_depth = 16
    
    cmd = [
        '../HDR_Clips/ffmpeg', # Adjust as necessary based on your FFmpeg installation
        '-i', video_path,
        '-f', 'image2pipe',
        '-pix_fmt', pix_fmt,
        '-vcodec', 'rawvideo', '-'
    ]

    pipe = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frames = []
    count = 0
    while True:
        # Read raw frame data
        raw_frame = pipe.stdout.read(width * height * bytes_per_pixel)
        if not raw_frame:
            break
        
        # Convert raw frame data to a NumPy array
        dtype = np.uint8 if bit_depth == 8 else np.uint16 # making sure we read the correct bit depth
        
        # frame 
        image = np.frombuffer(raw_frame, dtype=dtype)
        
        # Reshape the NumPy array to separate the Y, U, and V planes
        y_plane = image[:width*height].reshape((height, width))
        u_plane = image[width*height:width*height + (width//2)*(height//2)].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)
        v_plane = image[width*height + (width//2)*(height//2):].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)
        
        y = y_plane.astype(np.float32)
        u = u_plane.astype(np.float32)
        v = v_plane.astype(np.float32)

        # Convert YUV to RGB
        cb = u - 512
        cr = v - 512
        #print(y,cb,cr)
        r = y+1.4747*cr
        g = y-0.1645*cb-0.5719*cr
        b = y+1.8814*cb

        # Scale the values to the range [0, 1]
        r = (r-64)/(940-64)
        g = (g-64)/(940-64)
        b = (b-64)/(940-64)

        r = np.clip(r,0,1)
        g = np.clip(g,0,1)
        b = np.clip(b,0,1)
        
        image = np.stack((r,g,b),2)

        frames.append(image)
        
        count +=1
        #print("Frames Processed : ", count)
        return np.asarray(frames)  


#--------------------------------------------------------------*****--------------------------------------------------------------#
""" 
    Main function to extract frames from the HDR clips. 
"""
def main():
    parser = argparse.ArgumentParser(description="Extract frames from HDR clips")
    parser.add_argument("--num_frames", type=int, help="The number to process")
    parser.add_argument("--clips_path", type=str, help="Path to HDR clips")
    parser.add_argument("--save_path", type=str, help="Path to save the frames")
    # Parse the command-line arguments
    args = parser.parse_args()

    # Access the parsed number and perform some action
    files = sorted(glob(args.clips_path + "/*.mp4"))
    write_fdr = args.save_path 

    n = args.num_frames 

    # index for frame count
    start = 2000 * (n-1)
    end =  2000 * (n)
    #print(start,end)
    
    # getting the frames from the video and saving them in the folder
    for step,vid_path in enumerate(files[start:end]):
        print(step)
        
        start = time.time()
        # frames
        rgb_frames = np.float16(read_mp4_10bit(vid_path, 'tv'))
        # extracting n-frames
        random_number1 = random.randint(0, rgb_frames.shape[0]-5)
        idx = [random_number1]
        # saving the frames
        for id in idx : 
            np.save(write_fdr + vid_path.split("/")[-1][:-4] + "_frame_" +str(id)+".npy", rgb_frames[id])        
        print(time.time()-start)

if __name__ == "__main__":
    #files = sorted(glob("/corral/utexas/Automatic-Assessment/avinab/HDR_Clips/HDR_Clips_BitLadder/*.mp4"))
    #write_fdr = "/corral/utexas/Automatic-Assessment/avinab/HDR_Clips/HDR_Clips_Frames_RGB/"
    main()
