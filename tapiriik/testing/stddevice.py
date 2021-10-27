from unittest import TestCase
from tapiriik.services.devices import Device
from tapiriik.services.Decathlon.decathlon import DecathlonService

class StdDeviceTest(TestCase):

    def test_undefined_fit_device_and_manufacturer_return_default_values(self):

        undefined_fit_device_and_fit_manufacturer_std_device =  {
            "@context": "/v2/contexts/UserDevice",
            "@id": "/v2/user_devices/eu23218ff9b8010d294e",
            "@type": "UserDevice",
            "id": "eu23218ff9b8010d294e",
            "serial": "30:67:71:B8:DB:02",
            "fitManufacturer": None,
            "fitDevice": None,
            "model": "/v2/device_models/99",
            "firmware": "/v2/firmware/9928",
            "user": "/v2/users/eu200a4d76c4eab29015",
        }

        # When 
        hubDevice = DecathlonService.convertStdDeviceToHubDevice(undefined_fit_device_and_fit_manufacturer_std_device)

        # Then

        self.assertIsNotNone(hubDevice)
        self.assertIsInstance(hubDevice, Device)
        self.assertEqual(hubDevice.Manufacturer, "decathlon")
        self.assertEqual(hubDevice.Product, None)


    def test_fit_manufacturer_with_no_fit_device_return_provided_manufacturer_none_product(self):
        undefined_fit_device_and_decathlon_fit_manufacturer_std_device =  {
            "@context": "/v2/contexts/UserDevice",
            "@id": "/v2/user_devices/eu23218ff9b8010d294e",
            "@type": "UserDevice",
            "id": "eu23218ff9b8010d294e",
            "serial": "30:67:71:B8:DB:02",
            "fitManufacturer": 310,
            "fitDevice": None,
            "model": "/v2/device_models/99",
            "firmware": "/v2/firmware/9928",
            "user": "/v2/users/eu200a4d76c4eab29015",
        }

        # When 
        hubDevice = DecathlonService.convertStdDeviceToHubDevice(undefined_fit_device_and_decathlon_fit_manufacturer_std_device)

        # Then

        self.assertIsNotNone(hubDevice)
        self.assertIsInstance(hubDevice, Device)
        self.assertEqual(hubDevice.Manufacturer, "decathlon")
        self.assertIsNone(hubDevice.Product)


    def test_fit_manufacturer_with_fit_device_return_provided_manufacturer_and_provided_product(self):
        undefined_fit_device_and_decathlon_fit_manufacturer_std_device =  {
            "@context": "/v2/contexts/UserDevice",
            "@id": "/v2/user_devices/eu23218ff9b8010d294e",
            "@type": "UserDevice",
            "id": "eu23218ff9b8010d294e",
            "serial": "30:67:71:B8:DB:02",
            "fitManufacturer": 310,
            "fitDevice": 7,
            "model": "/v2/device_models/7",
            "firmware": "/v2/firmware/9928",
            "user": "/v2/users/eu200a4d76c4eab29015",
        }

        # When 
        hubDevice = DecathlonService.convertStdDeviceToHubDevice(undefined_fit_device_and_decathlon_fit_manufacturer_std_device)

        # Then

        self.assertIsNotNone(hubDevice)
        self.assertIsInstance(hubDevice, Device)
        self.assertEqual(hubDevice.Manufacturer, "decathlon")
        self.assertEqual(hubDevice.Product, 7)


    def test_undefined_fit_manufacturer_with_fit_device_return_default_manufacturer_and_none_product(self):
        undefined_fit_device_and_decathlon_fit_manufacturer_std_device =  {
            "@context": "/v2/contexts/UserDevice",
            "@id": "/v2/user_devices/eu23218ff9b8010d294e",
            "@type": "UserDevice",
            "id": "eu23218ff9b8010d294e",
            "serial": "30:67:71:B8:DB:02",
            "fitManufacturer": None,
            "fitDevice": 7,
            "model": "/v2/device_models/7",
            "firmware": "/v2/firmware/9928",
            "user": "/v2/users/eu200a4d76c4eab29015",
        }

        # When 
        hubDevice = DecathlonService.convertStdDeviceToHubDevice(undefined_fit_device_and_decathlon_fit_manufacturer_std_device)

        # Then

        self.assertIsNotNone(hubDevice)
        self.assertIsInstance(hubDevice, Device)
        self.assertEqual(hubDevice.Manufacturer, "decathlon")
        self.assertIsNone(hubDevice.Product)
        