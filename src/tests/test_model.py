import pandas as pd
from typing import List, Tuple

from  ..predictor.ctwin_after_plant_predictor import CTWinAfterPlantPredictor


class TestMainPredictor:
    _TEST_FILE_PATH = "src/tests/test_examples.csv"
    _BASE_PATH = "./model/"
    _MODEL_NAME = 'model.ctb'

    def test_predict(self) -> None:
        frame = pd.read_csv(self._TEST_FILE_PATH, sep=';')
        predictor = CTWinAfterPlantPredictor.load(self._BASE_PATH, self._MODEL_NAME)

        X = frame.drop(["CT-Win"], axis=1)
        answers = [int(x) for x in frame['CT-Win']]

        predicted = predictor.predict_round_raw(X.values.tolist())
        assert predicted == answers

test = TestMainPredictor()
test.test_predict()
