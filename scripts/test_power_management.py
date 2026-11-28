import unittest
from power_management import parse
class Tests(unittest.TestCase):
    def test_states(self):
        self.assertEqual(parse('ups.status: OL\nbattery.charge: 98\nbattery.runtime: 500\nups.serial: private'),{'state':'online','charge_percent':98.0,'runtime_seconds':500.0})
        for raw,state in [('OB DISCHRG','on_battery'),('OB LB','low_battery'),('FSD OL','low_battery'),('OFF','review'),('','unknown')]:
            self.assertEqual(parse('ups.status: '+raw)['state'],state)
        self.assertNotIn('charge_percent',parse('ups.status: OL\nbattery.charge: nan'))
if __name__=='__main__':unittest.main()
