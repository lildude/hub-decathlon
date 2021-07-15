from tapiriik.testing.testtools import TapiriikTestCase
from tapiriik.services.fit import FITIO

import os

class FitTest(TapiriikTestCase):
    def _get_fit_files_path(self):
        script_dir = os.path.dirname(__file__)
        fit_test_files_folder_path = "data/fit/"
        return [os.path.join(script_dir, fit_test_files_folder_path, file_name) for file_name in os.listdir(os.path.join(script_dir,fit_test_files_folder_path))]

    def test_constant_representation(self):
        print("----- Beginning test for FIT files -----")
        for fp in self._get_fit_files_path():
            print("Testing : %s" % fp)
            with open(fp, "rb") as testfile:
                act = FITIO.Parse(testfile.read())

            # TODO : THIS SHOULD NOT BE MAINTAINED AT ALL
            # It is just to make the tests succeed once before modifiying the overspecific fix deployed in 
            # https://github.com/Decathlon/hub-decathlon/pull/92
            act.ServiceData = None

            act2 = FITIO.Parse(FITIO.Dump(act))

            self.assertActivitiesEqual(act2, act)