from srds import ParameterizedDistribution as PDist

lan = PDist.lognorm((0.25, 0.35, 0.16))
wlan = PDist.lognorm((0.635, 1.18, 3.27))
business_isp = PDist.lognorm((0.87, 5.95, 1.21))
mobile_isp = PDist.lognorm((0.49, 16.2, 8.02))
