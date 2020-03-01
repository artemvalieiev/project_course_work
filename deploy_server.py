import logging

import tornado.ioloop
import tornado.web
from tornado.httpclient import AsyncHTTPClient

from src.deploy.api import Healthcheck, CTWinAfterPlantPredictor
from src.predictor import CTWinAfterPlantPredictor

logging.getLogger("transformers").setLevel(logging.ERROR)


MODEL_PATH = "model/"
MODEL_NAME = "model.ctb"
PORT = 1492


def make_app(predictor: CTWinAfterPlantPredictor, version: int) -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/predictor/healthcheck", Healthcheck, dict(version=version)),
            (r"/predictor/", CTWinAfterPlantPredictor, dict(predictor=predictor, version=version)),
        ]
    )


if __name__ == "__main__":
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", max_clients=100)
    http_client = AsyncHTTPClient()
    model_version = int(open("model.version").readline().rstrip())
    predictor = CTWinAfterPlantPredictor.load(MODEL_PATH, MODEL_NAME)
    app = make_app(predictor=predictor, version=model_version)
    app.listen(PORT)
    tornado.ioloop.IOLoop.current().start()
