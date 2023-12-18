# Data Collection, Preparation, and Processing for [HIRDO-VQA](https://arxiv.org/abs/2311.11059)

[![arXiv](https://img.shields.io/badge/arXiv-1234.56789-b31b1b.svg)](https://arxiv.org/abs/2311.11059)


> **HIDRO-VQA: High Dynamic Range Oracle for Video Quality Assessment**  
> Shreshth Saini, Avinab Saha, Alan C. Bovik  
> 3rd Workshop on Image/Video/Audio Quality in Computer Vision and Generative AI  
> WACV 2024

We provide IDs for all the videos used to create the dataset proposed in HIDRO-VQA. This repository prepares the final dataset from assumed pristine videos (make sure you download all videos first in highest available quality, i.e. 4K HDR). 

**NOTE:** We selectively curated the final set of videos to make sure it represents a diverse set of content. \
**NOTE:** **This is a more generic version of data preparation pipeline for HDR VQA tasks (Some modifications may be required for SDR).**

**CSV file with all the IDs is provided:** `./pristine_video_list.csv`.

## Prerequisites

Before running the code, make sure you have the following installed:

- Python 3.x
- pandas
- tqdm
- imageio_ffmpeg
- ffmpeg (keep binaries for in the same folder as the script to avoid any issues)

## Installation

1. Clone the repository to your local machine:

    ```bash
    git clone https://github.com/shreshthsaini/HIDRO-VQA-DATA.git
    ```

2. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1. Download all videos listed in `./pristine_video_list.csv`.

2. Filter and get the list for HDR and Non-HDR videos:

    ```bash
    python remove_non_HDR.py --video_path ./path/to/videos
    ```

    The script will create two csv files: `./HDR_videos.npy` and `./non_HDR_videos.npy`.

3. Final filtering to keep only High Quality videos:

    ```bash
    python filter_HDR.py --video_root ./path/to/videos

    ```

    The script will create a two csv files with all the meta: `HDR_vids_meta_data.csv` (full data in folder) and `HDR_meta_data_filtered_bfpHDRLIVE_4K_50fps.csv` (Only High quality).


4. Creating the Content separated clips from filtered videos (Check paper for details):
    
        ```bash
        python get_clips_MultiProcess.py --save_add ./path/to/save/clips
        ```
    
        The script will create a folder with all the clips in the output path.

5. Creating Bitladder to get distorted videos:

    ```bash
    python bitladder.py --bit_ladder_csv bitladder.csv --save_add ./path/to/save/distorted/videos
    ```

    The script will create a folder with all the distorted videos in the output path.

6. Finally, we extract frames (HIDRO-VQA uses only 1 frame each clip) to training: 

    ```bash
    python extract_frames.py --num_frames 1 --clips_path ./path/to/save/distorted/videos --save_path ./path/to/save/frames/
    ```




## Contributing

Contributions are welcome! If you find any issues or have suggestions for improvements, please open an issue or submit a pull request.

## Citation 
    @article{saini2023hidro,
    title={HIDRO-VQA: High Dynamic Range Oracle for Video Quality Assessment},
    author={Saini, Shreshth and Saha, Avinab and Bovik, Alan C},
    journal={arXiv preprint arXiv:2311.11059},
    year={2023}
    }

[Arxiv Link](https://arxiv.org/abs/2311.11059)

## License

This project is licensed under the [MIT License](LICENSE).
