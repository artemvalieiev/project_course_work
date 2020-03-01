import os

import joblib
from sklearn.datasets import fetch_20newsgroups
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, GroupShuffleSplit, StratifiedKFold, GroupKFold
from sklearn import metrics
from catboost import CatBoostClassifier, Pool
import pandas as pd
import glob
import os
import json
import numpy as np

MODEL_FOLDER = 'model'
MODEL_NAME = 'model.ctb'

#best parameters after best grid search  
CTB_MODEL_PARAMETERS = {
    'border_count': 192,
    'thread_count': 8,
    'random_seed': 42,
    'depth': 8,
    'od_wait': 30,
    'l2_leaf_reg': 10,
    'iterations': 500,
    'learning_rate': 0.05,
    'od_type': 'Iter'
 }


def save_column_mapping(column_name, mapping):
    with open('../' + MODEL_FOLDER + '/' + column_name + ".json", "w") as f:
        json_mapping = json.dumps(mapping)
        f.write(json_mapping)


def main() -> None:
    gameid_column = 'game_id'
    all_csv_file_pathes = glob.glob('../data/*/*.csv')
    all_frames = []
    for csv_filepath in all_csv_file_pathes:
        game_frame = pd.read_csv(csv_filepath,index_col=False, sep=';')
        game_frame.insert(0, 'game_id', csv_filepath)
        all_frames.append(game_frame)

    all_games = pd.concat(all_frames, axis=0, ignore_index=True)
    frame = all_games.copy()
    cols = frame.columns[frame.dtypes.eq('object')]

    for col in cols:
        frame[col] = frame[col].astype('category')
        if col is not gameid_column:
            column_mapping = dict(enumerate(frame[col].cat.categories))
            save_column_mapping(col, column_mapping)
        frame[col] = frame[col].cat.codes
    
    defects = frame.loc[frame["CT-Win"] == -1]
    frame.drop(defects.index, inplace=True)
    frame.dropna(axis='rows')

    y = frame["CT-Win"].astype(int)

    X = frame.drop(["CT-Win"], axis=1)
    X = X.drop(['game_id'],axis=1)

    all_column_map = {}
    for col_idx, col_name in enumerate(X.columns):
        all_column_map[col_idx] = col_name

    save_column_mapping('order.json', all_column_map)


    model = CatBoostClassifier(loss_function='Logloss', eval_metric = "AUC",
        border_count = CTB_MODEL_PARAMETERS['border_count'],
        thread_count= CTB_MODEL_PARAMETERS['thread_count'],
        random_seed=CTB_MODEL_PARAMETERS['random_seed'],
        depth = CTB_MODEL_PARAMETERS['depth'],
        od_wait = CTB_MODEL_PARAMETERS['od_wait'],
        l2_leaf_reg = CTB_MODEL_PARAMETERS['l2_leaf_reg'],
        iterations = CTB_MODEL_PARAMETERS['iterations'],
        learning_rate = CTB_MODEL_PARAMETERS['learning_rate'],
        od_type='Iter')
    ctb_data = Pool(X, y)
    model.fit(ctb_data, verbose=False)

    os.makedirs('./' + MODEL_FOLDER, exist_ok=True)
    model.save_model('./' + MODEL_FOLDER + '/' + MODEL_NAME)


if __name__ == "__main__":
    main()
