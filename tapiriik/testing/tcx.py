from tapiriik.testing.testtools import TestTools, TapiriikTestCase
from tapiriik.services.tcx import TCXIO

import os

class TCXTests(TapiriikTestCase):
    def test_constant_representation(self):
        ''' ensures that tcx import/export is symetric '''
        script_dir = os.path.dirname(__file__)
        rel_path = "data/test2.tcx"
        source_file_path = os.path.join(script_dir, rel_path)
        with open(source_file_path, 'r') as testfile:
            data = testfile.read()

        #svcA, other = TestTools.create_mock_services()
        #svcA.SupportsHR = svcA.SupportsCadence = svcA.SupportsTemp = True
        #svcA.SupportsPower = svcA.SupportsCalories = False
        #act = TestTools.create_random_activity(svcA, tz=True, withPauses=False)

        act = TCXIO.Parse(data.encode('utf-8'))
        new_data = TCXIO.Dump(act)
        act2 = TCXIO.Parse(new_data.encode('utf-8'))
        rel_path = "data/output1.tcx"
        new_file_path = os.path.join(script_dir, rel_path)
        with open(new_file_path, "w") as new_file:
            new_file.write(new_data)
        #act2.TZ = act.TZ  # we need to fake this since local TZ isn't defined in GPX files, and TZ discovery will flail with random activities
        #act2.AdjustTZ()
        #act.Stats.Distance = act2.Stats.Distance = None  # same here

        self.assertActivitiesEqual(act2, act)