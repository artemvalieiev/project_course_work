import os
from typing import List
import json
import glob

import numpy as np
from pandas import DataFrame
from catboost import CatBoostClassifier

class CTWinAfterPlantPredictor:
    def __init__(self, model: CatBoostClassifier, column_mappings: {}) -> None:
        self._model = model
        self.column_mappings = column_mappings
        self.CatBoostClassifier = CatBoostClassifier()


    @classmethod
    def load(cls, model_folder: str, model_name: str) -> "CTWinAfterPlantPredictor":
        cat_boost_classifier = CatBoostClassifier()
        model = cat_boost_classifier.load_model(os.path.join(model_folder) + model_name)

        all_mappings_file_paths = glob.glob('./model/*.json')
        mappings = {}
        for mapping_file_name in all_mappings_file_paths:
            with open(mapping_file_name, 'r') as map_file:
                value = json.load(map_file)
                _, key = os.path.split(mapping_file_name)
                key = key.replace('.json', '')
                mappings[key] = value

        return cls(model=model, column_mappings=mappings)

    def predict_round(self, samples: DataFrame ) -> List[int]:
        predictions = self._model.predict(samples)
        return [int(x) for x in predictions]

    def predict_round_raw(self, samples: List[List[str]]) -> List[int]:
        val = self._map_columns(samples)
        predictions = self._model.predict(val)
        return [int(x) for x in predictions]

    def predict_round_proba(self, samples: DataFrame) -> np.array:
        predictions = self._model.predict_proba(samples)
        return predictions

    def _map_columns(self, samples):
        values = []
        order = self.column_mappings['order']
        for row in samples:
            row_value = []
            for row_column_index, row_column_value in enumerate(row):
                try:
                    float_value = float(row_column_value)
                    row_value.append(float_value)
                except ValueError:
                    column = order[str(row_column_index)]
                    column_mapping = dict((v, k) for k, v in self.column_mappings[column].items())
                    row_value.append(column_mapping[row_column_value])
            values.append(row_value)

        return values





