""" 
Python Script to read HDR 10-bit video files and return a list of NumPy arrays representing each frame.
Since, some of the videos can be in HDR 10-bit format, we need to read them in a different way than the normal 8-bit videos.

NOTE: MP4 videos are normalized and whereas webm videos are not normalized. 

In case of 8-bit videos, we can use the following code to read the video:
    import imageio
    reader = imageio.get_reader(video_path)
    frames = [frame for frame in reader]
    print(f"Read {len(frames)} frames from the video.")

Or alternatively, we can use opecv to read the video:
    import cv2
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    print(f"Read {len(frames)} frames from the video.")


-- Created on Tue Nov 2022
-- Author: Shreshth Saini 

"""
import os
import imageio_ffmpeg as ffmpeg
import numpy as np 
import subprocess
import json

#-------------------------------------------------**********-------------------------------------------------# 
def check_video_range(video_path):
    """
    Check the range of an MP4 video file.

    Parameters:
    - video_path: str, path to the video file

    Returns:
    - str, either 'tv' or 'pc' based on the range used in the video file, or 'unknown' if the range could not be determined
    """
    try:
        # Run ffprobe to get video stream information in JSON format
        cmd = [
            'ffprobe', 
            '-v', 'quiet', 
            '-print_format', 'json', 
            '-show_streams', 
            video_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Parse the JSON output from ffprobe
        ffprobe_output = json.loads(result.stdout)
        
        # Get the color range from the first video stream
        streams = ffprobe_output.get('streams', [])
        for stream in streams:
            if stream.get('codec_type') == 'video':
                color_range = stream.get('color_range')
                if color_range:
                    return color_range
                else:
                    return 'unknown'
        return 'unknown'
    except Exception as e:
        print(f"An error occurred: {e}")
        return 'unknown'

#-------------------------------------------------**********-------------------------------------------------#
def verify_frames(frames):
    """
    Verify if a list of NumPy arrays correctly represents an HDR 10-bit video.

    Parameters:
    - frames: list of NumPy arrays, each representing a frame in the video

    Returns:
    - bool, True if the frames correctly represent an HDR 10-bit video, False otherwise
    """
    if not frames:
        print("No frames to verify.")
        return False

    # Check the data type of the frames
    if frames[0].dtype != np.float32:
        print("Incorrect data type.")
        return False

    # Check the range of pixel values
    min_value = np.min([np.min(frame) for frame in frames])
    max_value = np.max([np.max(frame) for frame in frames])
    
    if min_value < 0 or max_value > 1:
        print(f"Incorrect pixel value range: min={min_value}, max={max_value}")
        return False
    
    # Check if there are any values above the 8-bit maximum
    max_8bit_value = 255 / 1023
    if max_value <= max_8bit_value:
        print(f"No values above 8-bit maximum: max value={max_value}")
        return False

    print("The frames correctly represent an HDR 10-bit video.")
    return True

#-------------------------------------------------**********-------------------------------------------------#
#-------------------------------------------------**********-------------------------------------------------#
def read_mp4_10bit(video_path, range='tv'):
    # Get video metadata
    command_probe = [
        "ffprobe",
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
    # Read video frames and convert them to a NumPy array
    
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
        ffmpeg.get_ffmpeg_exe(),
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
        dtype = np.uint8 if bit_depth == 8 else np.uint16
        image = np.frombuffer(raw_frame, dtype=dtype)

        # Reshape the NumPy array to separate the Y, U, and V planes
        y_plane = image[:width*height].reshape((height, width))
        u_plane = image[width*height:width*height + (width//2)*(height//2)].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)
        v_plane = image[width*height + (width//2)*(height//2):].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)

        # Stack the Y, U, and V planes to create a 3D array (you might need to upsample the U and V planes)
        image = np.stack((y_plane, u_plane, v_plane), axis=-1)

        # Normalize the pixel values based on the determined range
        image = image.astype(np.float32)
        image = (image - offset) * scale
        image = np.clip(image, 0, 1)
        
        frames.append(image)
        
        count +=1
        print("Frames Processed : ", count)
    
    return frames    


#-------------------------------------------------**********-------------------------------------------------#
def read_webm_10bit(video_path):
    """Read a 10-bit HDR video file and return a list of NumPy arrays representing each frame.

    Args:
    video_path (str): The path to the HDR video file.

    Returns:
    list of np.ndarray: A list of NumPy arrays representing each frame in the video.
    """
    # Get video properties using FFprobe
    command_probe = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,pix_fmt",
        "-of", "csv=p=0",
        video_path
    ]
    
    result = subprocess.run(command_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    width, height, pix_fmt = result.stdout.strip().split(',')
    width, height = int(width), int(height)
    print(f"Video resolution: {width}x{height}", "pix fmt: ",pix_fmt)
    # Define FFmpeg command to extract raw video frames
    command = [
        "ffmpeg",
        '-i', video_path,
        '-f', 'image2pipe',
        '-pix_fmt', pix_fmt,  # maintain the original pixel format
        '-vcodec', 'rawvideo',
        '-'
    ]

    # Run FFmpeg command and capture output
    pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    frames = []

    # Calculate the number of bytes per frame
    bytes_per_frame = width * height * 3#1.5  # Adjust this based on the pixel format

    count = 0
    # Read each frame from the FFmpeg pipe
    while True:
        # Read raw data
        raw_image = pipe.stdout.read(bytes_per_frame)
        if not raw_image:
            break

        # Convert raw data to NumPy array
        image = np.frombuffer(raw_image, dtype='uint16')  # Adjust dtype based on the bit depth

        # Reshape the NumPy array to separate the Y, U, and V planes
        y_plane = image[:width*height].reshape((height, width))
        u_plane = image[width*height:width*height + (width//2)*(height//2)].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)
        v_plane = image[width*height + (width//2)*(height//2):].reshape((height//2, width//2)).repeat(2,axis=0).repeat(2,axis=1)

        # Stack the Y, U, and V planes to create a 3D array (you might need to upsample the U and V planes)
        image = np.stack((y_plane, u_plane, v_plane), axis=-1)

        #frames.append(image) #causes memory issue. use yield instead  
        #check the max and min range of the frame
        print("Max: ",np.max(image)," Min: ",np.min(image))
        count +=1
        print("Frames Processed : ", count)

    return frames

#-------------------------------------------------**********-------------------------------------------------#
def read_yuv_video(filename, width, height):
    """
    Read a 10-bit YUV HDR video file.
    
    Parameters:
    - filename: path to the YUV file.
    - width: width of the YUV frames.
    - height: height of the YUV frames.
    
    Returns:
    - y, u, v: Y, U, and V components as 3D numpy arrays.
    """
    
    # Calculate frame size for 10-bit
    frame_size = width * height * 2 + (width // 2 * height // 2) * 2 * 2
    
    # Calculate the number of frames based on file size
    num_frames = os.path.getsize(filename) // frame_size
    
    frames = []
    with open(filename, 'rb') as f:
        for i in range(num_frames):
            # Read Y component
            y_video = np.frombuffer(f.read(width * height * 2), dtype=np.uint16).reshape((height, width))
            
            # Read U component
            u_video = np.frombuffer(f.read(width // 2 * height // 2 * 2), dtype=np.uint16).reshape((height // 2, width // 2))
            
            # Read V component
            v_video = np.frombuffer(f.read(width // 2 * height // 2 * 2), dtype=np.uint16).reshape((height // 2, width // 2))

            # Stack the Y, U, and V components and append frame in frames list
            frames.append(np.stack((y_video, u_video, v_video), axis=-1))
            
        
    return frames


#-------------------------------------------------**********-------------------------------------------------#
def main(video_path, range_type='tv', format='any'):
    range_type = check_video_range(video_path)
    print(f"The video uses {range_type} range.")
    
    if format == 'mp4':
        # Read video frames
        frames = read_mp4_10bit(video_path, range_type)
    else:
        frames = read_webm_10bit(video_path)

    if frames is not None:
                print(f"Read {len(frames)} frames from the video.")
                # Verify the frames
                verify_frames(frames)

#-------------------------------------------------**********-------------------------------------------------#
if __name__ == "__main__":
    # video read
    video_path = '/scratch/4k_ref_Furniture.mp4'
    main(video_path)
    # video read
    video_path = "/media/3ckAESlpVTo_762.webm"
    main(video_path)
