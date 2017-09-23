This project is a Dota2 Env for OpenAI Gym as well as sample model

It is based on following works (thank you):
 - https://github.com/ModDota/Dota2AIFramework/
 - https://github.com/lightbringer/dota2ai
 - https://github.com/DarkSupremo/VConsoleLib.python
  
### Usage
To run it all (including model), you need 
- python 3
- python modules: gym, keras, tensorflow, numpy and their dependencies 
- dota2 client installed somewhere
- free 8080 port

To run:
1. Copy everything from "Game" folder to <Dota2 Install folder>\game\dota_addons\d2ai
2. Change DOTA_PATH in Server\d2env.py file to your exe/sh for dota2
3. Create folder Server\models, or comment out `self.model.save('models/episode_' + str(e) + '.bin')` in Server\server.py
4. Run `python server.py` from Server folder

It should start dota, automatically launch mod, and then allow model to play until it dies or 10 minutes pass

Then it will restart, and try again, until model gets 100 creeps or 1000 runs

Model is saved after each run into Server\models folder

Current model seems to be too dumb to not die from dire t1 :(