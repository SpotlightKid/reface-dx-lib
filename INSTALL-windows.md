# Windows Installation Instructions

## From the Git Reposirory

* Install [Python 3](https://www.python.org/downloads/windows/) (3.8 preferred, at least 3.6+)
* Install [git for windows](https://gitforwindows.org/) (optional)

```console
git clone https://github.com/SpotlightKid/reface-dx-lib
````

or download https://github.com/SpotlightKid/reface-dx-lib/archive/master.zip
and extract it.

Then:

```
cd reface-dx-lib
# or, if you downloaded & extracted the repo as a Zip archive:
# cd reface-dx-lib-master
python -m venv venv
.\venv\Scripts\activate
python -m pip -U pip setuptools wheel
python -m pip install PyQt5
.\build-win.bat
python -m pip install .[soundmondo]
```
