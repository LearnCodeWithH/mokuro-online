# mokuro-online
Flask app to run mokuro in a dedicated server, including a API

# Instalation

1. Install Python (>= 3.10)
2. Install Poetry (>= 1.6.1)
3. Clone this repository
4. Enter the repository folder (`cd mokuro-online`)
5. Install dependencies with poetry (`poetry install`)
6. Generate a random *SECRET_KEY* and add it to `config.py`
7. Edit Anything more you want in `config.py`


You can see the commands here:

```bash
# Step 3 and 4, if you have GIT installed
git clone https://github.com/imsamuka/mokuro-online.git
cd mokuro-online

# Step 5 and 6
poetry install
sed -i "s/SECRET_KEY = .*/SECRET_KEY = '$(python3 -c 'import secrets; print(secrets.token_hex())')'/" config.py

# Step 7: Edit the file `config.py`
```

## Running locally

It's very simple, since it's local by default.

```bash
poetry run gunicorn
```

## Running on a server

You can run it whoever you want. The thing you have to care the most is to use *multi-threading* instead of *multi-processing*, because the app depends on it.

This is an example `/etc/systemd/system/mokuro-online.service` file for running this when the server starts. It will create a unix socket on `/home/ubuntu/mokuro-online/mokuro-online.sock`, and you can for example, use nginx to proxy everything to it with SSL.

```ini
[Unit]
Description=Gunicorn instance to serve mokuro-online
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/mokuro-online
ExecStart=/usr/bin/poetry run gunicorn --bind unix:app.sock -m 007 "app:create_app('production')"

[Install]
WantedBy=multi-user.target
```

```nginx
server {
    listen 80;
    server_name your_domain www.your_domain;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/mokuro-online/app.sock;
        client_max_body_size 150M;
    }
}
```

## Running on Docker

Build and run the Docker image:

```
docker build -t local/mokuro-online-cuda -f ./Dockerfile .
docker run --gpus all --publish $APP_PORT:$APP_PORT --env APP_PORT=$APP_PORT --detach local/mokuro-online-cuda
```

### With CUDA support

You'll need to make sure you have everything set up for docker to access your GPU [as outlined here.](https://saturncloud.io/blog/how-to-use-gpu-from-a-docker-container-a-guide-for-data-scientists-and-software-engineers/)

```
docker run --gpus all --publish $APP_PORT:$APP_PORT --env APP_PORT=$APP_PORT --detach local/mokuro-online-cuda
```
