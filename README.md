# telecloud-server

Telecloud server provides a REST API for interacting with Telegram to store media.

## Installation

```bash
git clone https://github.com/estebanthi/telecloud-server
cd telecloud-server
pip install -r requirements.txt
```

Then, you need to setup a Telegram application to get an api id and an api hash: https://core.telegram.org/api/obtaining_api_id.

You also need to setup a MongoDB database: https://www.mongodb.com.

Finally, you can replace the values in `config.sample.yaml` with your values and rename it to `config.yaml`.

## Usage

Check the [documentation of the api](https://tasty-baboon-13.redoc.ly/).