# lua-helpers
This little project is made for people who just want to download a Lua version and get on with their day.

Note: This is still a WIP, far from done. Just chose Python to come up with a rough example.

## Requirements
`python <= 3.12` (3.12 will deprecate distutils, I'm on version 3.9.7)  
`distutils` for the **ccompiler**  
```bash
pip install -r requirements.txt
```

## Usage
`python .\main.py --download --lua <version> [--force]`  

-----------------------------

`--force [if the lua version already exists, it will replace it]`
`--lua -l [tells it to download Lua]`