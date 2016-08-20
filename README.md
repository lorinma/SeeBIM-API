# SeeBIM-API

This service is used for querying BIM data (IFC entities) in mongoDB through a RESTful API.

## Installation:
### install conda env and dev env
sudo apt-get update; sudo apt-get install vim git -y; sudo git clone https://github.com/lorinma/dockeride.git /usr/src/dockeride; ln -sf /usr/src/dockeride/.bashrc ~/.bashrc; ln -sf /usr/src/dockeride/.vim ~/.vim; ln -sf /usr/src/dockeride/.vimrc ~/.vimrc; wget –quiet -O miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh; bash miniconda.sh -b -p $HOME/miniconda; rm -rf miniconda.sh; source ~/.bashrc;

### install eve and dotenv
sudo pip install git+git://github.com/nicolaiarocci/eve.git 
sudo python-dotenv==0.5.0

### setup credentials in env
touch .env

MONGO_HOST=xxxx
MONGO_PORT=0000
MONGO_USERNAME=xxxx
MONGO_PASSWORD=xxxx
MONGO_DBNAME=xxxx

### fire the app
python run.py