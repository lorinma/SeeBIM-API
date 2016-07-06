# RESTfulIFC

This service is used for querying BIM data (IFC entities) in mongoDB through a RESTful API.

## Installation:
### install conda env and dev env
sudo apt-get update; sudo apt-get install vim git -y; sudo git clone https://github.com/lorinma/dockeride.git /usr/src/dockeride; ln -sf /usr/src/dockeride/.bashrc ~/.bashrc; ln -sf /usr/src/dockeride/.vim ~/.vim; ln -sf /usr/src/dockeride/.vimrc ~/.vimrc; wget –quiet -O miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh; bash miniconda.sh -b -p $HOME/miniconda; rm -rf miniconda.sh; source ~/.bashrc;

### install eve
sudo pip install git+git://github.com/nicolaiarocci/eve.git

### install ifcopenshell
conda config --add channels http://conda.anaconda.org/DLR-SC

conda config --add channels http://conda.anaconda.org/lorinma

conda install ifcopenshell=0.5dev

### install trimesh required libs
sudo apt-get install cmake openscad blender libspatialindex-dev libgeos-dev -y

sudo pip install svg.path meshpy pyglet shapely Rtree

### install remaining packages
sudo pip install -r requirements.txt

### setup credentials in env
touch .env

MONGO_HOST=xxxx

MONGO_PORT=0000

MONGO_USERNAME=xxxx

MONGO_PASSWORD=xxxx

MONGO_DBNAME=xxxx

TRIMBLE_API_URL=xxxx

TRIMBLE_EMAIL=xxxx

TRIMBLE_KEY=xxxx

### fire the app
python run.py

pip install gspread
pip install --upgrade oauth2client
pip install PyOpenSSL

see: http://gspread.readthedocs.io/en/latest/oauth2.html

### A related project:
https://github.com/lorinma/SeeBIM
