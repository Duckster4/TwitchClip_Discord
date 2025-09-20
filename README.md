# TwitchClip_Discord
Sends clips from twitch to discord webhook

Required python packages: dotenv, typing, moviepy

To initialize: 

- run the json_encryption.py
- supply with your twitch channels id, you can use a tool like [streamweasels](https://www.streamweasels.com/tools/convert-twitch-username-%20to-user-id/)
- supply with your discord webhook url
- supply with your application auoth token for your channel (or any account with the editor role for set channel)
    can be done with a link like https://id.twitch.tv/oauth2/authorize?client_id=YOURCLIENTID&redirect_uri=http://localhost&response_type=token&scope=editor:manage:clips

Also put your application id in the CLIENT_ID variable of the .env, or change the get_clips to use your client_id

Each time you run the get_clips.py script, the clips get send to your webhook. Clips that have been send already, won't be send again
