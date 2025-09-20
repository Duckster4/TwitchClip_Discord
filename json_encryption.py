import json
import base64
import hashlib
import secrets
from cryptography.fernet import Fernet
from typing import Union, List, Dict

with open('.key', 'r') as f:
    encryption_key = f.read()
if encryption_key == None:
    raise ValueError("No encryption key was found")

key = encryption_key.encode()

def encrypt_value(value: str) -> str:
    """Encrypts a string value using a derived key from the salt."""
    cipher = Fernet(key)
    return cipher.encrypt(value.encode()).decode()

def decrypt_value(value: str) -> str:
    """Decrypts a string value using a derived key from the salt."""
    cipher = Fernet(key)
    return cipher.decrypt(value.encode()).decode()

def process_json(json_data: Dict[str, List[Dict[str, Union[str, int]]]]):
    """Processes the JSON data, encrypting and decrypting as necessary."""
    for broadcaster in json_data.get("broadcasters", []):
        for key, value in broadcaster.items():
            if isinstance(value, str) and value:  # Encrypt non-empty strings
                if "discord_webhook_url" in key or "twitch_oauth_token" in key:
                    broadcaster[key] = encrypt_value(value)
    return json_data

def get_decrypted(file_path: str) -> Union[Dict[str, List[Dict[str, Union[str, int]]]], None]:
    """Reads a JSON file, decrypts specified fields, and returns the JSON object."""
    if key == None or key == "":
        with open('.key', 'r') as f:
            encryption_key = f.read()
        if encryption_key == None:
            raise ValueError("No encryption key was found")
    
    with open(file_path, 'r') as file:
        json_data = json.load(file)

    for broadcaster in json_data.get("broadcasters", []):
        for key_, value in broadcaster.items():
            if isinstance(value, str) and value:
                if "discord_webhook_url" in key_ or "twitch_oauth_token" in key_:
                    broadcaster[key_] = decrypt_value(value)
    
    return json_data

def generate_salt() -> str:
    """Generates a random salt."""
    return secrets.token_hex(16)

if __name__ == "__main__":
    try:
        broadcasters_data = get_decrypted('broadcasters.json')
    except FileNotFoundError:
        broadcasters_data = {"broadcasters": []}
    
    if broadcasters_data == None:
        print("Decryption failed, either try to fix this, or delete the file to generate a new one")
        exit()
        
    print("Decrypted Broadcasters Data:", broadcasters_data)
        
    twitch_id = int(input("Enter Twitch ID: "))
    discord_webhook_url = input("Enter Discord Webhook URL: ")
    twitch_oauth_token = input("Enter Twitch Auth Token: ")
    
    new_broadcaster = {
        "twitch_id": twitch_id,
        "discord_webhook_url": discord_webhook_url,
        "twitch_oauth_token": twitch_oauth_token
    }
    
    broadcasters_data["broadcasters"].append(new_broadcaster)
    
    new_key = Fernet.generate_key().decode()
    with open('.key', 'w') as f:
        f.write(new_key)
    key = new_key.encode()

    # Encrypt the sample JSON data
    encrypted_json = process_json(broadcasters_data)
    print("Encrypted JSON:", json.dumps(encrypted_json, indent=2))

    # Save the encrypted JSON to a file
    with open('broadcasters.json', 'w') as outfile:
        json.dump(encrypted_json, outfile, indent=4)