import json
import unittest

from src import create_app
from src.config.env_config import Config


class AppTestCase(unittest.TestCase):
    # pylint: disable=C0103,R0904
    """This class represents the app test case"""

    def setUp(self):
        """Define test variables and initialize app."""
        config_class = Config
        config_class.DB_NAME = "march_madness_test"
        self.app = create_app(config_class)
        self.client = self.app.test_client

    def tearDown(self):
        """Executed after tests are all done"""

    def test_home(self):
        response = self.client().get("/")
        data = json.loads(response.data)
        actual = data["message"]

        expected = "Welcome!"

        self.assertEqual(response.status_code, 200)
        self.assertEqual(actual, expected)
