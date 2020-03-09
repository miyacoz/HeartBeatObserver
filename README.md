# HeartBeatObserver

Would let you know on Discord whether your websites are alive or not. It will ping you (or someone else, as you like) in a specified channel of your Discord server when it fails to know your websites are in good health.

Also, it would inform you about the load averages of the server where you install HeartBeatObserver.

## Setup

### .env

|Name|Optional?|Description|Example|
|---|---|---|---|
|`WEBHOOK_URL`||The Discord's webhook url which HeartBeatObserver would post messages to.|`https://discordapp.com/api/webhooks/{webhook.id}/{webhook.token}`<br />For details, see [Discord's documentation](https://discordapp.com/developers/docs/resources/webhook).|
|`OBSERVATION_TARGETS`|*Y*|Comma-separated urls of websites that you want to observe. Each url has to include its scheme (such as `https:`).|`https://www.zeppel.biz/`<br />`https://www.zeppel.net/,https://www.zeppel.biz/this/path/does/not/exist/really?maybe=true`|
|`USER_IDS_FOR_PINGING`|*Y*|Comma-separated integer ids of users who you want to ping. The user id is different from username like `miyaco` and `miyaco#8492`.<br /> If it is blank, HeartBeatObserver would not ping anyone even if it needs to do so.|`12345`<br />`12345,23456`|

## How to use

You can invoke it directly from your command line after you give it the executable flag (`chmod 744 heartbeatobserver.py`.).

You need it's invoked periodically and automatically? You can add it into your crontab or something like that, I guess? XD
