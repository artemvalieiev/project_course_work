Project idea is predict whether CT side will win round after bomb being planted by terrorists in CS:GO competitions.

### Data

All data comes parsed from dem files.
DEM (short for demo) is the Source demo file format. Used in conjunction with the Source recorder to record demos, which contain recorded events that can be edited and played back in-game. Demos can be edited to change camera angles, speed up, slow down, play music, and other functions.

Game demos were scrubbed from hltv.org website, which contains demos for latest major competitions on cs go.
Then demos was parsed using C# library called demoinfo.

### Features

Since I have the whole demo replay, I can generate *almost* any feature for current tick. 

I will start from base scoreboard features that you can see when you press scoreboard key on map like:

- Current Round
- CT/T Score
- Current money of players in your team
- Current equipment value of players alive in team
- Does CT team has kits for faster defuse and how many
- Current map
- How many players alive on the moment when bomb has been planted.

I also added to useful features like:

- Travel distance to bomb for each player
- On which side bomb has planted
- Does players have any other utilities (grenades, flashes, smokes) 
- Which guns players has 

### Model

CatBoost library was used to predict features, 
since it is performed better than LightGBM, XGBoost on my data.

### Result metric

              precision    recall  f1-score   support

           0       0.91      0.94      0.92      1321
           1       0.78      0.69      0.73       403
    accuracy       -         -         0.88      1724
    macro avg      0.84      0.82      0.83      1724
    weighted avg   0.88      0.88      0.88      1724

 