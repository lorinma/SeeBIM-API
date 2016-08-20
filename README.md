# SeeBIM-core

Extract geometry and topology features of a BIM model in an IFC file and store them in a mongodb

## Installation:
### install conda env and dev env
sudo apt-get update; sudo apt-get install vim git -y; sudo git clone https://github.com/lorinma/dockeride.git /usr/src/dockeride; ln -sf /usr/src/dockeride/.bashrc ~/.bashrc; ln -sf /usr/src/dockeride/.vim ~/.vim; ln -sf /usr/src/dockeride/.vimrc ~/.vimrc; wget –quiet -O miniconda.sh https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh; bash miniconda.sh -b -p $HOME/miniconda; rm -rf miniconda.sh; source ~/.bashrc;

### install numpy and ifcopenshell
conda config --add channels http://conda.anaconda.org/DLR-SC; conda config --add channels http://conda.anaconda.org/lorinma; conda install numpy ifcopenshell=0.5dev -y;

### install trimesh and its required libs
sudo apt-get install cmake openscad blender libspatialindex-dev libgeos-dev -y
sudo pip install trimesh[all]

### install python-fcl
conda install python-fcl -y;

### nstall eve
sudo pip install git+git://github.com/nicolaiarocci/eve.git
sudo pip install python-dotenv==0.5.0

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

TRIMBLE_FolderID=xxxx