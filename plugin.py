"""
EV Charge Control python plugin for Domoticz
Author: szelessavmuhely.hu,
Version: 1.0.0 (september 18, 2026) 

<plugin key="EV_CC" name="EV Charge Control _ Autótöltő vezérlés" author="szelessavmuhely.hu" version="1.0.0">
	<description>
		<h2>EV Charge Control _ Autótöltő vezérlés</h2><br/>
		<br/>
		<br/>
		Autótöltő automatikus vezérlése időzítés. / Automatic EV charger control based on scheduling.
		<br/>
	</description>
	<params>
		<param field="Address" label="Domoticz IP Address" width="200px" required="true" default="127.0.0.1"/>
		<param field="Port" label="Port" width="40px" required="true" default="8080"/>
		<param field="Username" label="Username" width="200px" required="false" default=""/>
		<param field="Password" label="Password" width="200px" required="false" default=""/>
		<param field="Mode1" label="Töltő kapcsoló / Charger Switch (csv list of idx)" width="200px" default=""/>
		<param field="Mode3" label="Log" width="200px" default="">
			<options>
				<option label="Normal" value="Normal" default="true"/>
				<option label="Verbose" value="Verbose"/>
				<option label="Debug - Python Only" value="2"/>
				<option label="Debug - Basic" value="62"/>
				<option label="Debug - Basic+Messages" value="126"/>
				<option label="Debug - Connections Only" value="16"/>
				<option label="Debug - Connections+Queue" value="144"/>
				<option label="Debug - All" value="-1"/>
			</options>
		</param>
	</params>
</plugin>
"""
import Domoticz
import json
from urllib import parse, request
from datetime import datetime, timedelta
import time
import math
import base64
import itertools
import re
import os
import heapq

class deviceparam:

	def __init__(self, unit, nvalue, svalue):
		self.unit = unit
		self.nvalue = nvalue
		self.svalue = svalue

class switchparam:

	def __init__(self, idx, command):
		self.idx = idx
		self.command = command

class TranslationLoader:

	def __init__(self, language="en"):
		self.translations = self.load_translations(language)
		if not self.translations:
			Domoticz.Debug("An error occurred while loading the translations!")
			self.translations = self.load_translations("en") 

	def load_translations(self, language):
		file_path = os.path.join(Parameters["HomeFolder"], f'evcc_translate_{language}.json')
		try:
			with open(file_path, 'r', encoding='utf-8') as file:
				return json.load(file)
		except (FileNotFoundError, json.JSONDecodeError) as e:
			Domoticz.Debug(f"Error loading the file '{file_path}': {e}")
			return {} 

	def t(self, text):
		return self.translations.get(text, text)  # If there is no translation, it returns with the original text

class BasePlugin:

	def __init__(self):

		self.debug = True
		self.statussupported = hasattr(Domoticz, "Status")
		self.switchcreated = []
		self.statuscreated = []
		self.start_time = None
		self.start_minute = None
		self.duration_minutes = None
		return


	def onStart(self):

		self.location = Settings["Location"].split(";")
		
		tl = TranslationLoader(Parameters["Language"])

		self.watering_valve = parseCSV(Parameters["Mode1"])

		self.soil_moisture_meter = parseCSV(Parameters["Mode2"])

		# állítsa be a megfelelő naplózási szintet
		try:
			debuglevel = int(Parameters["Mode3"])
		except ValueError:
			debuglevel = 0
			self.loglevel = Parameters["Mode3"]
		if debuglevel != 0:
			self.debug = True
			Domoticz.Debugging(debuglevel)
			DumpConfigToLog()
			self.loglevel = "Verbose"
		else:
			self.debug = False
			Domoticz.Debugging(0)

		devicecreated = []
		if 1 not in Devices:
			Options = {"LevelActions": "||",
				"LevelNames": tl.t("Off|Charge On|Charge Off|Automatic On|Automatic Off"),
				"LevelOffHidden": "true",
				"SelectorStyle": "1"}
			Domoticz.Device(Name=tl.t("Charger operating mode"), Unit=1, TypeName="Selector Switch", Image=9, Options=Options, Used=1).Create()
			devicecreated.append(deviceparam(1, 0, "40"))
			self.addfavorite(Devices[1].ID)
		if 2 not in Devices:
			Options = {"LevelActions": "||",
				"LevelNames": tl.t("Off|00|01|02|03|04|05|06|07|08|09|10|11|12|13|14|15|16|17|18|19|20|21|22|23|"),
				"LevelOffHidden": "true",
				"SelectorStyle": "1"}
			Domoticz.Device(Name=tl.t("Start time"), Unit=2, TypeName="Selector Switch", Image=21, Options=Options, Used=1).Create()
			devicecreated.append(deviceparam(2, 0, "190"))
		if 3 not in Devices:
			Options = {"LevelActions": "||",
				"LevelNames": tl.t("Off|00|05|10|15|20|25|30|35|40|45|50|55"),
				"LevelOffHidden": "true",
				"SelectorStyle": "1"}
			Domoticz.Device(Name=tl.t("Start minute"), Unit=3, TypeName="Selector Switch", Image=21, Options=Options, Used=1).Create()
			devicecreated.append(deviceparam(3, 0, "10"))
		if 4 not in Devices:
			Options = {"LevelActions": "||",
				"LevelNames": tl.t("Off|30 min|1 hour|1.5 hours|2 hours|3 hours|4 hours|5 hours|6 hours|8 hours|10 hours|12 hours"),
				"LevelOffHidden": "true",
				"SelectorStyle": "1"}
			Domoticz.Device(Name=tl.t("Duration"), Unit=4, TypeName="Selector Switch", Image=21, Options=Options, Used=1).Create()
			devicecreated.append(deviceparam(4, 0, "60"))
		if 5 not in Devices:
			Domoticz.Device(Name="Charge switch on-off", Unit=5, Type=244, Subtype=73, Switchtype=0, Used=0).Create()
			devicecreated.append(deviceparam(5, 0, "0"))
		if 6 not in Devices:
			Domoticz.Device(Name=tl.t("Charge restart lockout"), Unit=6,  Type=243, Subtype=22, Used=1).Create()
			devicecreated.append(deviceparam(6, 0, tl.t("No restart lockout")))
			self.addfavorite(Devices[6].ID)

		for device in devicecreated:
			Devices[device.unit].Update(nValue=device.nvalue, sValue=device.svalue)

		self.parameters()


	def onStop(self):
		Domoticz.Debugging(0)


	def onCommand(self, Unit, Command, Level, Color):

		Domoticz.Debug("onCommand called for Unit {}: Command '{}', Level: {}".format(Unit, Command, Level))

		nvalue = 1 if Level > 0 else 0
		svalue = str(Level)

		Devices[Unit].Update(nValue=nvalue, sValue=svalue)

		if Unit in (1, 2, 3): # újrainditás, ha megváltozik a vezérlésimód
			self.parameters()


	def onHeartbeat(self):

		self.switchcreated.clear()
		self.statuscreated.clear()

		# aktuális idő percben
		now = datetime.now()
		now_minutes = now.hour * 60 + now.minute

		# kezdési idő percben
		start_minutes = self.start_time * 60 + self.start_minute

		# időszak vége
		end_minutes = (start_minutes + self.duration_minutes) % (24 * 60)

		# benne vagyunk-e az időintervallumban
		if start_minutes < end_minutes:
			in_time = start_minutes <= now_minutes < end_minutes
		else:
			# éjfélen átnyúló időszak
			in_time = now_minutes >= start_minutes or now_minutes < end_minutes


		# Manuális be
		if Devices[1].sValue == "10":
			self.ChargingSwitch(True)

		# Manuális ki
		elif Devices[1].sValue == "20":
			self.ChargingSwitch(False)

		# Automatikus On
		elif Devices[1].sValue == "30":
			if in_time:
				self.ChargingSwitch(True)
			else:
				self.ChargingSwitch(False)

		# Automatikus Off
		elif Devices[1].sValue == "40":
			if in_time:
				self.ChargingSwitch(False)
			else:
				self.ChargingSwitch(True)

		self.switchcommand()
		self.statuscommand()


	def WriteLog(self, message, level="Normal"):

		if (self.loglevel == "Verbose" and level == "Verbose") or level == "Status":
			if self.statussupported:
				Domoticz.Status(message)
			else:
				Domoticz.Log(message)
		elif level == "Normal":
			Domoticz.Log(message)

	def addfavorite(self, deviceidx):

		idx = deviceidx
		DomoticzAPI("idx={}&isfavorite=1&param=makefavorite&type=command".format(idx))

	def removefavorite(self, deviceidx):

		idx = deviceidx
		DomoticzAPI("idx={}&isfavorite=0&param=makefavorite&type=command".format(idx))


	def ChargingSwitch(self, switch):

		command = "On" if switch else "Off"

		if switch:
			nvalue = 1
			svalue = "On"
		else:
			nvalue = 0
			svalue = "Off"
		
		Devices[5].Update(nValue=nvalue, sValue=svalue)

		for idx in self.watering_valve:
			self.switchappend(idx,command)

	def switchappend(self,idx,command):

		notInList = True
		for switch in self.switchcreated:
			if switch.idx == idx:
				Domoticz.Debug("Ez a kapcsoló már benne van a listában "+ format(idx) +" | "+ format(command))
				if command == "On":
					Domoticz.Debug("%s az érték felül kell írni a %s értékkel" % (switch.command, command))
					switch.command = command
				else:
					Domoticz.Debug("Marad a %s érték" % command)
				notInList = False
				break
		if notInList:
			Domoticz.Debug("Ez a kapcsoló még nincs a listában, hozzá kell adni " + format(idx) +" | "+ format(command))
			self.switchcreated.append(switchparam(idx, command))


	def switchcommand(self):

		tl = TranslationLoader(Parameters["Language"])

		# A legnagyobb még hátralévő tiltási idő
		lockout_remaining = 0

		devicesAPI = DomoticzAPI(
			"type=devices&filter=light&order=Name" 
			if float(Parameters["DomoticzVersion"]) <= 2023.1 
			else "type=command&param=getdevices&filter=light&order=Name"
		)

		if devicesAPI:
			for switch in self.switchcreated:

				for device in devicesAPI["result"]:
					deviceidx = int(device["idx"])

					if deviceidx == switch.idx:

						Domoticz.Debug(
							"Kapcsoló " + format(switch.idx) + " " + format(device["Status"])
						)

						# -------------------------------------------------
						# 30 perces újraindítási védelem
						# -------------------------------------------------

						if switch.command == "On" and device["Status"] == "Off":

							try:
								last_update = datetime.fromisoformat(device["LastUpdate"])

								elapsed = datetime.now() - last_update
								elapsed_minutes = elapsed.total_seconds() / 60.0

								Domoticz.Debug(
									"Kapcsoló idx " + format(switch.idx) +
									" | Utolsó állapotváltozás óta: {:.1f} perc".format(elapsed_minutes)
								)

								if elapsed_minutes < 30:
									remaining = math.ceil(30 - elapsed_minutes)

									if remaining > lockout_remaining:
										lockout_remaining = remaining

									Domoticz.Debug(
										"Kapcsoló idx " + format(switch.idx) +
										" | Bekapcsolás tiltva, még " +
										format(remaining) + " perc"
									)

									continue

							except Exception as e:
								Domoticz.Error(
									"Kapcsoló idx " + format(switch.idx) +
									" | LastUpdate feldolgozási hiba: " +
									format(e)
								)

								# Biztonsági okból hiba esetén sem kapcsoljuk be
								continue


						# -------------------------------------------------
						# Kapcsolás
						# -------------------------------------------------

						if device["Status"] != format(switch.command):

							Domoticz.Debug(
								"Kapcsoló idx " + format(switch.idx) +
								" | Szükség van kapcsolásra: " +
								format(switch.command)
							)

							DomoticzAPI(
								"type=command&param=switchlight&idx={}&switchcmd={}".format(
									switch.idx,
									switch.command
								)
							)

						else:
							Domoticz.Debug(
								"Kapcsoló idx " + format(switch.idx) +
								" | Nincs szükség kapcsolásra"
							)


		# -------------------------------------------------
		# Újraindítási tiltás szöveges státusza - Unit 6
		# -------------------------------------------------

		if lockout_remaining > 0:
			status_text = tl.t("Restart blocked, {} minutes remaining").format(lockout_remaining)
			status_nValue = 4
		else:
			status_text = tl.t("No restart lockout")
			status_nValue = 1

		if Devices[6].sValue != status_text or Devices[6].nValue != status_nValue:
			Devices[6].Update(
				nValue=status_nValue,
				sValue=status_text
			)

			Domoticz.Debug(
				"Charge restart lockout frissítve -> {} (nValue={})".format(
					status_text,
					status_nValue
				)
			)

	def switchstatus(self,idx,command):
		notInList = True
		for statusflag in self.statuscreated:
			if statusflag.idx == idx:
				Domoticz.Debug("Ez a status már benne van a listában "+ format(idx) +" | "+ format(command))
				if command == "On":
					Domoticz.Debug("%s az érték felül kell írni a %s értékkel" % (statusflag.command, command))
					statusflag.command = command
				else:
					Domoticz.Debug("Marad a %s érték" % command)
				notInList = False
				break
		if notInList:
			Domoticz.Debug("Ez a status még nincs a listában, hozzá kell adni " + format(idx) +" | "+ format(command))
			self.statuscreated.append(switchparam(idx, command))

	def statuscommand(self):
		devicesAPI = DomoticzAPI(
			"type=devices&filter=light&order=Name" 
			if float(Parameters["DomoticzVersion"]) <= 2023.1 
			else "type=command&param=getdevices&filter=light&order=Name"
		)
		if devicesAPI:
			for statusflag in self.statuscreated:
				# A status aktuális állapotonak megállapítása és, annak ellenőrzésére, hogy már a kívánt állapotban van-e?
				for device in devicesAPI["result"]:  # elemzi a kapcsolóeszközt
					deviceidx = int(device["idx"])
					if deviceidx == statusflag.idx:  # ez az a kapcsoló
						Domoticz.Debug("Status " + format(statusflag.idx)+" "+format(device["Status"]))
						if device["Status"] != format(statusflag.command) :
							Domoticz.Debug("Szükség van status váltásra ")
							if format(statusflag.command) == "On":
								nValue = 1
							else :
								nValue = 0

							self.UpdateDevice(device["Unit"],nValue,statusflag.command)
						else: 
							Domoticz.Debug("Nincs szükség status váltásra ")


	def parameters(self):

		if Devices[2].sValue == "10" :
			self.start_time = 0
		elif Devices[2].sValue == "20" :
			self.start_time = 1
		elif Devices[2].sValue == "30" :
			self.start_time = 2
		elif Devices[2].sValue == "40" :
			self.start_time = 3
		elif Devices[2].sValue == "50" :
			self.start_time = 4
		elif Devices[2].sValue == "60" :
			self.start_time = 5
		elif Devices[2].sValue == "70" :
			self.start_time = 6
		elif Devices[2].sValue == "80" :
			self.start_time = 7
		elif Devices[2].sValue == "90" :
			self.start_time = 8
		elif Devices[2].sValue == "100" :
			self.start_time = 9
		elif Devices[2].sValue == "110" :
			self.start_time = 10
		elif Devices[2].sValue == "120" :
			self.start_time = 11
		elif Devices[2].sValue == "130" :
			self.start_time = 12
		elif Devices[2].sValue == "140" :
			self.start_time = 13
		elif Devices[2].sValue == "150" :
			self.start_time = 14
		elif Devices[2].sValue == "160" :
			self.start_time = 15
		elif Devices[2].sValue == "170" :
			self.start_time = 16
		elif Devices[2].sValue == "180" :
			self.start_time = 17
		elif Devices[2].sValue == "190" :
			self.start_time = 18
		elif Devices[2].sValue == "200" :
			self.start_time = 19
		elif Devices[2].sValue == "210" :
			self.start_time = 20
		elif Devices[2].sValue == "220" :
			self.start_time = 21
		elif Devices[2].sValue == "230" :
			self.start_time = 22
		elif Devices[2].sValue == "240" :
			self.start_time = 23
		
		if Devices[3].sValue == "10" :
			self.start_minute = 0
		elif Devices[3].sValue == "20" :
			self.start_minute = 5
		elif Devices[3].sValue == "30" :
			self.start_minute = 10
		elif Devices[3].sValue == "40" :
			self.start_minute = 15
		elif Devices[3].sValue == "50" :
			self.start_minute = 20
		elif Devices[3].sValue == "60" :
			self.start_minute = 25
		elif Devices[3].sValue == "70" :
			self.start_minute = 30
		elif Devices[3].sValue == "80" :
			self.start_minute = 35
		elif Devices[3].sValue == "90" :
			self.start_minute = 40
		elif Devices[3].sValue == "100" :
			self.start_minute = 45
		elif Devices[3].sValue == "110" :
			self.start_minute = 50
		elif Devices[3].sValue == "120" :
			self.start_minute = 55

		if Devices[4].sValue == "10":
			self.duration_minutes = 30
		elif Devices[4].sValue == "20":
			self.duration_minutes = 60
		elif Devices[4].sValue == "30":
			self.duration_minutes = 90
		elif Devices[4].sValue == "40":
			self.duration_minutes = 120
		elif Devices[4].sValue == "50":
			self.duration_minutes = 180
		elif Devices[4].sValue == "60":
			self.duration_minutes = 240
		elif Devices[4].sValue == "70":
			self.duration_minutes = 300
		elif Devices[4].sValue == "80":
			self.duration_minutes = 360
		elif Devices[4].sValue == "90":
			self.duration_minutes = 480
		elif Devices[4].sValue == "100":
			self.duration_minutes = 600
		elif Devices[4].sValue == "110":
			self.duration_minutes = 720

global _plugin
_plugin = BasePlugin()


def onStart():
	global _plugin
	_plugin.onStart()


def onStop():
	global _plugin
	_plugin.onStop()


def onCommand(Unit, Command, Level, Color):
	global _plugin
	_plugin.onCommand(Unit, Command, Level, Color)


def onHeartbeat():
	global _plugin
	_plugin.onHeartbeat()


# Plugin utility functions ---------------------------------------------------

def parseCSV(strCSV):

	listvals = []
	for value in strCSV.split(","):
		try:
			val = int(value)
		except:
			pass
		else:
			listvals.append(val)
	return listvals


def DomoticzAPI(APICall):

	resultJson = None
	url = "http://{}:{}/json.htm?{}".format(Parameters["Address"], Parameters["Port"], parse.quote(APICall, safe="&="))
	Domoticz.Debug("Calling domoticz API: {}".format(url))
	try:
		req = request.Request(url)
		if Parameters["Username"] != "":
			Domoticz.Debug("Add authentification for user {}".format(Parameters["Username"]))
			credentials = ('%s:%s' % (Parameters["Username"], Parameters["Password"]))
			encoded_credentials = base64.b64encode(credentials.encode('ascii'))
			req.add_header('Authorization', 'Basic %s' % encoded_credentials.decode("ascii"))

		response = request.urlopen(req)
		if response.status == 200:
			resultJson = json.loads(response.read().decode('utf-8'))
			if resultJson["status"] != "OK":
				Domoticz.Error("Domoticz API returned an error: status = {}".format(resultJson["status"]))
				resultJson = None
		else:
			Domoticz.Error("Domoticz API: http error = {}".format(response.status))
	except:
		Domoticz.Error("Error calling '{}'".format(url))
	return resultJson


# Generic helper functions
def DumpConfigToLog():
	for x in Parameters:
		if Parameters[x] != "":
			Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
	Domoticz.Debug("Device count: " + str(len(Devices)))
	for x in Devices:
		Domoticz.Debug("Device:" + str(x) + " - " + str(Devices[x]))
		Domoticz.Debug("Device ID: '" + str(Devices[x].ID) + "'")
		Domoticz.Debug("Device Name: '" + Devices[x].Name + "'")
		Domoticz.Debug("Device nValue: " + str(Devices[x].nValue))
		Domoticz.Debug("Device sValue: '" + Devices[x].sValue + "'")
		Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
	return
