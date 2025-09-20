from dotenv import load_dotenv
import requests
import os
import json
import sqlite3
from typing import Union, List, Dict
import re
import asyncio
from moviepy import VideoFileClip
from json_encryption import get_decrypted

def get_clip_uris(CLIENT_ID: str, broadcaster_id: int, ACCESS_TOKEN: str, after: Union[str, None]) -> Union[List[Dict[str, Union[str, int, bool]]], None]:
    url = f'https://api.twitch.tv/helix/clips?broadcaster_id={broadcaster_id}{f'&started_at={after}' if after != None else ""}'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200 or response.json()["data"] == None:
        return response.json()["data"]
    else:
        print(f"Failed to get clips: {response.status_code} - {response.text}")
        
def download_clips(CLIENT_ID: str, client_user_id: str, clip_name_dict: Dict[str, str], clip_ids: List[str], ACCESS_TOKEN: str, broadcaster_id: int) -> Dict[str, Union[str, None]]:
    suffix = ''.join(f'&clip_id={clip_id}' for clip_id in clip_ids)
    url = f'https://api.twitch.tv/helix/clips/downloads?editor_id={client_user_id}&broadcaster_id={broadcaster_id}{suffix}'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200 or response.json()["data"] == None:
        clips = response.json()["data"]
        if clips == None or len(clips) == 0:
            return  {}
        
        clip_paths = {}
        
        for clip in clips:
            if clip["landscape_download_url"] != None:
                clip_paths[clip["clip_id"]] = download_clip(clip_name_dict[clip["clip_id"]], clip["landscape_download_url"])
            elif clip["portrait_download_url"] != None:
                clip_paths[clip["clip_id"]] = download_clip(clip_name_dict[clip["clip_id"]], clip["portrait_download_url"])
            else:
                clip_paths[clip["clip_id"]] = None
                
        return clip_paths
    else:
        print(f"Failed to get clips: {response.status_code} - {response.text}")
    return {}

def normalize_filename(filename: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.lower()
    filename = filename.replace(' ', '_')
    filename = filename.strip()
    
    max_length = 255
    if len(filename) > max_length:
        filename = filename[:max_length]
    
    return filename

def compress_video(input_file, output_file, target_size_mb=7):
    print(f"compressing {input_file}")
    target_size_bytes = target_size_mb * 1024 * 1024
    video = VideoFileClip(input_file)
    current_bitrate = video.size[0] * video.size[1] * 30 * 0.07
    new_bitrate = (target_size_bytes * 8) / video.duration
    new_bitrate_kbps = int(new_bitrate / 1000)
    
    if new_bitrate > current_bitrate:
        new_bitrate = current_bitrate
    
    video.write_videofile(output_file, bitrate=f"{new_bitrate_kbps}k", codec='libx264', audio_codec='aac')

def download_clip(clip_name: str, url: str) -> Union[str, None]:
    clip_name = normalize_filename(clip_name)
    if not clip_name.endswith('.mp4'):
        clip_name += '.mp4'

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(f'clips/{clip_name}', 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
                
        if os.path.getsize(f'clips/{clip_name}') / (1024 * 1024) > 8:
            compress_video(f'clips/{clip_name}', f'clips/comp.{clip_name}')
            clip_name = f'comp.{clip_name}'

        print(f"Downloaded: {clip_name}")
        return f'clips/{clip_name}'
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    
def get_user_pfp(CLIENT_ID: str, ACCESS_TOKEN: str, twitch_id: str):
    url = f'https://api.twitch.tv/helix/users?id={twitch_id}'
    
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {ACCESS_TOKEN}'
    }

    response = requests.get(url, headers=headers)
    try:
        return response.json()["data"][0]["profile_image_url"]
    except:
        print(f"Failed to get pfp: {response.status_code} - {response.text}")
        return ""
        
class DiscordMessage:
    def __init__(self, clip_id: str, broadcaster_id: int, file_path: str, title: str, url: str, creator_name: str, creator_id: str, is_featured: bool):
        self.clip_id = clip_id
        self.broadcaster_id = broadcaster_id
        self.file_path = file_path
        self.title = title
        self.url = url
        self.creator_name = creator_name
        self.creator_id = creator_id
        self.is_featured = is_featured
        
    def __str__(self):
        return self.title
async def send_messages_via_webhook(webhook_url, CLIENT_ID: str, ACCESS_TOKEN: str, messages: List[DiscordMessage]):
    results = []
    
    for message in messages:
        print(f"Sending message: {str(message)}")
        
        embed = {
            "description": f"<{message.url}>\n{"The attachment was compressed" if message.file_path.__contains__("comp.") else ""}",
            "author": {
                "name": f"by: {message.creator_name}",
                "icon_url": f"{get_user_pfp(CLIENT_ID, ACCESS_TOKEN, message.creator_id)}"
            },
            "title": message.title,
            "color": 16711680 if message.is_featured else 4732984
        }
        
        payload = {
            "content": "",
            "embeds": [embed]
        }
        
        files = {}
        if message.file_path:
            files = {'file': open(message.file_path, 'rb')}
            
        json_payload = json.dumps(payload)
            
        response = requests.post(webhook_url, data={'payload_json': json_payload}, files=files)
        
        if response.status_code == 200:
            results.append(True)
        else:
            print(f"Failed to send message: {response.status_code} - {response.text}")
            results.append(False)
    
    return results
    
async def main():
    dotenv_path = '.env'
    load_dotenv(dotenv_path)

    CLIENT_ID = os.getenv('CLIENT_ID')

    if not CLIENT_ID:
        raise TypeError("No CLIENT_ID could be found, missing .env?")
    
    broadcaster_info = get_decrypted("broadcasters.json")
    if broadcaster_info == None:
        raise ValueError('No decriptable configs found')

    db_name = "clips.db"

    for broadcaster in broadcaster_info["broadcasters"]:
        client_user_id = str(broadcaster["twitch_client_id"])
        if client_user_id == "":
            client_user_id = str(broadcaster["twitch_id"])
        
        with sqlite3.connect(db_name) as conn:
            cursor = conn.cursor()
            
            query = "SELECT clip_id, created_at FROM clips WHERE channel_id = ? ORDER BY created_at DESC LIMIT 1"
            cursor.execute(query, (broadcaster["twitch_id"],))
            result = cursor.fetchone()
            if result == None:
                result = (None, None)

            data = get_clip_uris(CLIENT_ID, int(broadcaster["twitch_id"]), str(broadcaster["twitch_oauth_token"]), result[1])
            if data == None:
                print("No clips found")
                data = [] 
            data = [clip for clip in data if clip["id"] != result[0]]
            
            if len(data) == 0:
                print("No new clips found")
            else: 
                clip_ids = [str(clip["id"]) for clip in data]
                clip_name_dict = {str(clip['id']): str(clip['title']) for clip in data}
                file_path_dict = {}
                for i in range(0, len(clip_ids), 10):
                    batch = clip_ids[i:i + 10]
                    batch_file_path_dict = download_clips(CLIENT_ID, client_user_id, clip_name_dict, batch, str(broadcaster["twitch_oauth_token"]), int(broadcaster["twitch_id"]))
                    file_path_dict.update(batch_file_path_dict)
                
                temp_clips = []
                for clip in data:
                    if file_path_dict[str(clip["id"])]:
                        clip["path"] = file_path_dict[str(clip["id"])]
                        temp_clips.append(clip)
                        
                data = temp_clips
                
                query = "INSERT INTO clips (channel_id, clip_id, title, created_at, url, creator_id, creator_name, is_featured, file_path, send) VAlUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)"
                for clip in data:
                    cursor.execute(query, (broadcaster["twitch_id"], clip["id"], clip["title"], clip["created_at"], clip["url"], clip["creator_id"], clip["creator_name"], clip["is_featured"], clip["path"]))
            
            query = "SELECT clip_id, channel_id, file_path, title, url, creator_name, creator_id, is_featured FROM clips WHERE send = 0 ORDER BY created_at ASC"
            cursor.execute(query)
            send_clips = cursor.fetchall()
            if len(send_clips) > 0:
                print(f"Sending {len(send_clips)} clips to discord")
            
            msgs = []
            for clip in send_clips:
                msgs.append(DiscordMessage(clip[0], int(clip[1]), clip[2], clip[3], clip[4], clip[5], clip[6], int(clip[7]) == 1))
            
            update = await send_messages_via_webhook(broadcaster["discord_webhook_url"], CLIENT_ID, str(broadcaster["twitch_oauth_token"]), msgs)
            update_query = "UPDATE clips SET send = 1 WHERE clip_id = ?"
            for i in range(len(msgs)):
                if update[i]: 
                    cursor.execute(update_query, (msgs[i].clip_id,))
                
if __name__ == "__main__":
    asyncio.run(main())