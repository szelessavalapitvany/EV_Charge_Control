var hardwareReq   = "/json.htm?type=command&param=gethardware";
var tempReq       = "/json.htm?type=command&param=graph&sensor=temp&range=day&idx=";
var tempName      = "/json.htm?type=command&param=getdevices&filter=temp&order=Name";
var switchReq     = "/json.htm?type=command&param=getlightlog&range=day&idx=";
var switchName    = "/json.htm?type=command&param=getdevices&filter=lightlog&order=Name";
var devicesReq    = "/json.htm?type=command&param=getdevices";
var PercentageReq = "/json.htm?type=command&param=graph&sensor=Percentage&range=day&idx=";
var utilityReq    = "/json.htm?type=command&param=graph&sensor=counter&range=day&idx=";
var windReq       = "/json.htm?type=command&param=graph&sensor=wind&range=day&idx=";
var setpointReq   = "/json.htm?type=command&param=getdevices&rid=";
var settingsReg   = "/json.htm?type=command&param=getsettings";
var rainReq       = "/json.htm?type=command&param=graph&sensor=rain&range=day&idx=";


if (typeof window.ToltoKontroller === 'undefined') {
	class ToltoKontroller {
		constructor() {
			this.name = "";
			this.toltokapcsolo = undefined;
			this.soilmoisture = undefined;
		}
	}
	window.ToltoKontroller = ToltoKontroller;
}

if (typeof window.Tolto === 'undefined') {
	class Tolto {
		constructor() {
			this.historic = undefined;
			this.isDimmer = false;
		}
	}
	window.Tolto = Tolto;
}

Date.prototype.yyyymmdd_hhmm = function() {
	var mm = this.getMonth() + 1;
	var dd = this.getDate();
	var hh = this.getHours();
	var min = this.getMinutes();

	return [
		this.getFullYear(),
		(mm > 9 ? '' : '0') + mm,
		(dd > 9 ? '' : '0') + dd,
		'_',
		(hh > 9 ? '' : '0') + hh,
		(min > 9 ? '' : '0') + min
	].join('');
};

function getRequestParam(name) {
	var req = location.search;

	if (req.length == 0) {
		req = location.href;
	}

	if (name = (new RegExp('[?&]' + encodeURIComponent(name) + '=([^&]*)')).exec(req))
		return decodeURIComponent(name[1]);
}

if (typeof window.ChargerSwitch === 'undefined') {
	class ChargerSwitch {
		constructor() {
			this.historic = [];
		}
	}
	window.ChargerSwitch = ChargerSwitch;
}

function getTolto() {
	nodata = true;

	var langakt = "en";
	var request = proto + address + ":" + port.toString() + hardwareReq;
	var toltok = [];

	$.ajax({
		url: request,
		async: false,
		success: function(result) {

			for (var i = 0; i < result.result.length; i++) {

				if (result.result[i].Extra == "EV_CC" && result.result[i].Enabled == "true") {

					nodata = false;

					var tolto = new Tolto();
					var name = result.result[i].Name;

					tolto.name = name;
					tolto.id = result.result[i].idx;

					var innerRequest = proto + address + ":" + port.toString() + devicesReq;

					$.ajax({
						url: innerRequest,
						async: false,
						success: function(resultTolto) {

							tolto.host = result.result[i].Address;
							tolto.uname = result.result[i].Username;
							tolto.pass = result.result[i].Password;
							tolto.port = result.result[i].Port;

							for (var j = 0; j < resultTolto.result.length; j++) {

								if (tolto.id == resultTolto.result[j].HardwareID) {

									var device = resultTolto.result[j];

									switch (Number(device.Unit)) {
										case 1:
											tolto.mode = device;
											break;

										case 2:
											tolto.startHour = device;
											break;

										case 3:
											tolto.startMinute = device;
											break;

										case 4:
											tolto.duration = device;
											break;

										case 5:
											tolto.chargeSwitch = device;
											break;

										case 6:
											tolto.restartBlock = device;
											break;
									}
								}

								// Töltőkapcsoló naplóadatainak lekérése

								if (tolto.id == resultTolto.result[j].HardwareID && resultTolto.result[j].Unit == 5) {

									request = proto + address + ":" + port.toString() + switchReq + resultTolto.result[j].idx;

									$.ajax({
										url: request,
										async: false,
										success: function(resultChargerSwitch) {

											var now = Date.now();
											var minDate = now - (24 * 60 * 60 * 1000);
											var currentStatus = resultTolto.result[j].Status;

											tolto.chargerswitch = [];

											if (!resultChargerSwitch || resultChargerSwitch.status !== "OK") {
												return;
											}

											var history = Array.isArray(resultChargerSwitch.result)
												? resultChargerSwitch.result
												: [];

											// Naplóadatok időrendi rendezése

											history = history.map(function(item) {
												return {
													...item,
													time: new Date(item.Date.replace(' ', 'T')).getTime()
												};
											}).filter(function(item) {
												return Number.isFinite(item.time) &&
													item.time <= now &&
													(item.Status === "On" || item.Status === "Off");
											}).sort(function(a, b) {
												return a.time - b.time;
											});

											// Az időszak kezdetén érvényes állapot

											var firstStatus = null;

											history.forEach(function(item) {
												if (item.time <= minDate) {
													firstStatus = item.Status;
												}
											});

											// Kizárólag az elmúlt 24 óra eseményei

											tolto.chargerswitch = history.filter(function(item) {
												return item.time > minDate;
											}).map(function(item) {
												return {
													Date: new Date(item.time).toISOString(),
													Status: item.Status
												};
											});

											// Ha nem történt kapcsolás, az utolsó
											// frissítés alapján ellenőrizzük az állapotot

											if (firstStatus === null && tolto.chargerswitch.length === 0) {

												var lastUpdate = new Date(
													(resultTolto.result[j].LastUpdate || '').replace(' ', 'T')
												).getTime();

												if (Number.isFinite(lastUpdate) && lastUpdate <= minDate) {
													firstStatus = currentStatus;
												}
											}

											// Az időszak kezdőpontja

											if (firstStatus === "On" || firstStatus === "Off") {
												tolto.chargerswitch.unshift({
													Date: new Date(minDate).toISOString(),
													Status: firstStatus
												});
											}

											// Aktuális kapcsolási állapot

											if (currentStatus === "On" || currentStatus === "Off") {
												tolto.chargerswitch.push({
													Date: new Date(now).toISOString(),
													Status: currentStatus
												});
											}
										}
									});
								}
							}
						}
					});

					toltok.push(tolto);
				}
			}
		}
	});

	//console.log("toltok", toltok);

	return toltok;
}