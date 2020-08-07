# HeartBeatObserver

Would let you know on Discord whether your websites are alive or not. It will ping you (or someone else, as you like) in a specified channel of your Discord server when it fails to know your websites are in good health.

## Setup

HeartBeatObserver supports `config.yaml` or `.env` as its configuration file. If some key or value is not found in `config.yaml`, that in `.env` will be used instead.

### Keys and values

|Name and type in `config.yaml`|Name in `.env`|Optional?|Description|Example|
|---|---|---|---|---|
|`webhook_url`<br />String|`WEBHOOK_URL`||The Discord's webhook url which HeartBeatObserver would post messages to.|`https://discordapp.com/api/webhooks/{webhook.id}/{webhook.token}`<br />For details, see [Discord's documentation](https://discordapp.com/developers/docs/resources/webhook).|
|`observation_targets`<br />List of string|`OBSERVATION_TARGETS`|*Y*|Comma-separated urls of websites that you want to observe. Each url has to include its scheme (such as `https:`).|`https://www.zeppel.biz/`<br />`https://www.zeppel.net/,https://www.zeppel.biz/this/path/does/not/exist/really?maybe=true`|
|`user_ids_for_pinging`<br />List of integer|`USER_IDS_FOR_PINGING`|*Y*|Comma-separated integer ids of users who you want to ping. The user id is different from username like `miyaco` and `miyaco#8492`.<br /> If it is blank, HeartBeatObserver would not ping anyone even if it needs to do so.|`12345`<br />`12345,23456`|
|`number_of_attempts`<br />Integer|`NUMBER_OF_ATTEPMTS`|*Y*|Integer value (>= `1`) which determines how many times HeartBeatObserver will try the health-check for the given websites until success.<br />Default value for this parameter is `1`.|`5`|
|`attempt_interval`<br />Integer|`ATTEMPT_INTERVAL`|*Y*|Integer value (>= `1`) which determines how many seconds HeartBeatObserver will wait until the next attempt of the health-check.<br />Default value for this parameter is `1`.|`5`|
|`alert_ssl_expires_in`<br />Integer|`ALERT_SSL_EXPIRES_IN`|*Y*|Integer value (>= `1`) which determines how many days before the observation target's SSL certificate expires and when HeartBeatObserver should start alerting.<br />If your SSL certificates expires on 31st January, and you set this value to `31`, HeartBeatObserver will ping you on and after 1st January. If you set this value to `30`, HeartBeatObserver will ping you on and after 2nd January.|`15`|

## How to use

You can invoke it directly from your command line after you give it the executable flag (`chmod 744 heartbeatobserver.py`.).

You need it's invoked periodically and automatically? You can add it into your crontab or something like that, I guess? XD
