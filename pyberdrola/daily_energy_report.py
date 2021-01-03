from bs4 import BeautifulSoup
from datetime import date, timedelta
import pprint
import requests
from requests import Session
import sys
import smtplib
from email.message import EmailMessage
import secrets as ss

pp = pprint.PrettyPrinter(indent=4)

yesterday_dt = date.today() - timedelta(days = 1)
yesterday_str = yesterday_dt.strftime('%d-%m-%Y00:00:00')

class ResponseException(Exception):
    pass

class LoginException(Exception):
    pass

class SessionException(Exception):
    pass

class NoResponseException(Exception):
    pass

class SelectContractException(Exception):
    pass

class Iber:
    __domain = "https://www.i-de.es"
    __login_url = __domain + "/consumidores/rest/loginNew/login"
    __daily_consumption_detail_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosConsumo/fechaInicio/" + yesterday_str + "/colectivo/USU/frecuencia/horas/acumular/false"
    __watthourmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
    __icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
    __contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
    __contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
    __contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
    __headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; charset=utf-8",
        'content-type': "application/json; charset=utf-8",
        'cache-control': "no-cache"
    }

    def __init__(self):
        """Iber class __init__ method."""
        self.__session = None

    def login(self, user, password):
        """Creates session with your credentials"""
        self.__session = Session()
        login_data = "[\"{}\",\"{}\",null,\"Linux -\",\"PC\",\"Chrome 77.0.3865.90\",\"0\",\"\",\"s\"]".format(user, password)
        response = self.__session.request("POST", self.__login_url, data=login_data, headers=self.__headers)
        if response.status_code != 200:
            self.__session = None
            raise ResponseException("Response error, code: {}".format(response.status_code))
        json_response = response.json()
        if json_response["success"] != "true":
            self.__session = None
            raise LoginException("Login error, bad login")
        if json_response["success"] == "true":
            #print("Login OK")
            pass

    def __check_session(self):
        if not self.__session:
            raise SessionException("Session required, use login() method to obtain a session")

    def watthourmeter(self):
        """Returns your current power consumption."""
        self.__check_session()
        response = self.__session.request("GET", self.__watthourmeter_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        #pp.pprint(json_response)
        try:
            current_wh_value = json_response['valMagnitud']
        except:
            #e = sys.exc_info()[0]
            current_wh_value = None
        try:
            current_switch_value = json_response['valInterruptor']
        except:
            #e = sys.exc_info()[0]
            current_switch_value = None
        try:
            total_wh_value = json_response['valLecturaContador']
        except:
            #e = sys.exc_info()[0]
            total_wh_value = None
        return (current_wh_value,
            current_switch_value,
            total_wh_value)

    def daily_consumption(self):
        """Returns your current power consumption."""
        self.__check_session()
        response = self.__session.request("GET", self.__daily_consumption_detail_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        #pp.pprint(json_response)
        try:
            date_value = json_response["fechaPeriodo"][:10]
        except:
            #e = sys.exc_info()[0]
            date_value = None
        try:
            date_esp_human_readable_value = json_response["periodoMuestra"]
        except:
            #e = sys.exc_info()[0]
            date_esp_human_readable_value = None
        try:
            units_value = json_response["y"]["unidadesConsumo"]
        except:
            #e = sys.exc_info()[0]
            units_value = None
        try:
            daily_total_value = json_response["acumulado"]
        except:
            #e = sys.exc_info()[0]
            daily_total_value = None
        hours_dict = {}
        for num in range(0, 24):
            try:
                hours_dict[f'{(num):02}'] = json_response["y"]["data"][0][num]["valor"]
            except:
                #e = sys.exc_info()[0]
                hours_dict[f'{(num):02}'] = None
        return(date_value, date_esp_human_readable_value,
            units_value, daily_total_value, hours_dict)
        #return (json_response['valMagnitud'],
        #    json_response['valInterruptor'],
        #    json_response['valLecturaContador'])

    def icpstatus(self):
        """Returns the status of your ICP."""
        self.__check_session()
        response = self.__session.request("POST", self.__icp_status_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        #pp.pprint(json_response)
        try:
            current_power_switch_value = json_response["icp"]
        except:
            #e = sys.exc_info()[0]
            current_power_switch_value = None
        #print(current_power_switch_value)
        if current_power_switch_value == "trueConectado":
            return True
        else:
            return False

    def contracts(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contracts_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["success"]:
            return json_response["contratos"]

    def contract(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_detail_url, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        return response.json()

    def contractselect(self, id):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_selection_url + id, headers=self.__headers)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if not json_response["success"]:
            raise SelectContractException

i = Iber()
login = Iber.login(i, user = ss._iber_user, password = ss._iber_pass)
Iber.contractselect(i, ss._iber_contract)
icp_status = Iber.icpstatus(i)

#print(icp_status)
#TEST

(date_value, date_esp_human_readable_value,
     units_value, daily_total_value,
     hours_dict) = Iber.daily_consumption(i)

#print(date_value, date_esp_human_readable_value,
#     units_value, daily_total_value,
#     hours_dict)

current_watts, current_switch, total_watts = Iber.watthourmeter(i)

if int(float(daily_total_value)) > 0:
    alarm = True
    alarm_str = "AYER HA HABIDO CONSUMO!"
else:
    alarm = False
    alarm_str = "Parece que ayer NO hubo ningun consumo."

max_value = 0
max_value_keys_list = []
for key in hours_dict:
    #print("{0}: {1:8d} {2}".format(key, int(float(hours_dict[key])), units_value))
    if int(float(hours_dict[key])) > max_value:
        max_value = int(float(hours_dict[key]))
    else:
        pass
    #xstr += repr("A las {0} el consumo fue de: {1:8d} {2}\n").format(key, int(float(hours_dict[key])), units_value)
#max_value
dec_value = round(max_value / 10)
graphics_dict = {}
for key in hours_dict:
    if dec_value != 0:
        pos = round(int(float(hours_dict[key]))/dec_value)
    else:
        pos = 0
    #print("{0}: {1:10} {2:8d} {3}".format(key, "*" * pos, int(float(hours_dict[key])), units_value))
    graphics_dict[key] = pos

#hourly_report_str = ""
#for key in hours_dict:
#    #print("A las {0} el consumo fue de: {1:8d} {2}".format(key, int(float(hours_dict[key])), units_value))
#    hourly_report_str += repr("A las {0} el consumo fue de: {1:8d} {2}\n").format(key, int(float(hours_dict[key])), units_value)

report_str = """
     Buenos dias,

     Informacion para el contrato {0}.\r\n
     Tu consumo de ayer,
     {1},
     fue de -- {2} {3} --.

     {52}

     El detalle por horas es el siguiente:
     HORA -           - TOTAL (Wh)
     00:   {4:10} {5:8}
     01:   {6:10} {7:8}
     02:   {8:10} {9:8}
     03:   {10:10} {11:8}
     04:   {12:10} {13:8}
     05:   {14:10} {15:8}
     06:   {16:10} {17:8}
     07:   {18:10} {19:8}
     08:   {20:10} {21:8}
     09:   {22:10} {23:8}
     10:   {24:10} {25:8}
     11:   {26:10} {27:8}
     12:   {28:10} {29:8}
     13:   {30:10} {31:8}
     14:   {32:10} {33:8}
     15:   {34:10} {35:8}
     16:   {36:10} {37:8}
     17:   {38:10} {39:8}
     18:   {40:10} {41:8}
     19:   {42:10} {43:8}
     20:   {44:10} {45:8}
     21:   {46:10} {47:8}
     22:   {48:10} {49:8}
     23:   {50:10} {51:8}

     Recuerda que esto es aun una PoC.
     Comprueba en la web si estos datos son correctos.

""".format(ss._iber_contract, date_esp_human_readable_value.upper(),
    int(float(daily_total_value)), units_value,
    "*" * graphics_dict['00'] + " " * (10 - graphics_dict['00']), int(float(hours_dict['00'])),
    "*" * graphics_dict['01'] + " " * (10 - graphics_dict['01']), int(float(hours_dict['01'])),
    "*" * graphics_dict['02'] + " " * (10 - graphics_dict['02']), int(float(hours_dict['02'])),
    "*" * graphics_dict['03'] + " " * (10 - graphics_dict['03']), int(float(hours_dict['03'])),
    "*" * graphics_dict['04'] + " " * (10 - graphics_dict['04']), int(float(hours_dict['04'])),
    "*" * graphics_dict['05'] + " " * (10 - graphics_dict['05']), int(float(hours_dict['05'])),
    "*" * graphics_dict['06'] + " " * (10 - graphics_dict['06']), int(float(hours_dict['06'])),
    "*" * graphics_dict['07'] + " " * (10 - graphics_dict['07']), int(float(hours_dict['07'])),
    "*" * graphics_dict['08'] + " " * (10 - graphics_dict['08']), int(float(hours_dict['08'])),
    "*" * graphics_dict['09'] + " " * (10 - graphics_dict['09']), int(float(hours_dict['09'])),
    "*" * graphics_dict['10'] + " " * (10 - graphics_dict['10']), int(float(hours_dict['10'])),
    "*" * graphics_dict['11'] + " " * (10 - graphics_dict['11']), int(float(hours_dict['11'])),
    "*" * graphics_dict['12'] + " " * (10 - graphics_dict['12']), int(float(hours_dict['12'])),
    "*" * graphics_dict['13'] + " " * (10 - graphics_dict['13']), int(float(hours_dict['13'])),
    "*" * graphics_dict['14'] + " " * (10 - graphics_dict['14']), int(float(hours_dict['14'])),
    "*" * graphics_dict['15'] + " " * (10 - graphics_dict['15']), int(float(hours_dict['15'])),
    "*" * graphics_dict['16'] + " " * (10 - graphics_dict['16']), int(float(hours_dict['16'])),
    "*" * graphics_dict['17'] + " " * (10 - graphics_dict['17']), int(float(hours_dict['17'])),
    "*" * graphics_dict['18'] + " " * (10 - graphics_dict['18']), int(float(hours_dict['18'])),
    "*" * graphics_dict['19'] + " " * (10 - graphics_dict['19']), int(float(hours_dict['19'])),
    "*" * graphics_dict['20'] + " " * (10 - graphics_dict['20']), int(float(hours_dict['20'])),
    "*" * graphics_dict['21'] + " " * (10 - graphics_dict['21']), int(float(hours_dict['21'])),
    "*" * graphics_dict['22'] + " " * (10 - graphics_dict['22']), int(float(hours_dict['22'])),
    "*" * graphics_dict['23'] + " " * (10 - graphics_dict['23']), int(float(hours_dict['23'])),
    alarm_str)

#print(report_str)

s = smtplib.SMTP(host = ss._email_host, port = ss._email_port)
s.starttls()
s.login(ss._email_user, ss._email_pass)

msg = EmailMessage()
msg.set_content(report_str)

msg['Subject'] = 'Consumo diario de contadores'
msg['From'] = ss._email_from
msg['To'] = ss._email_to_list

# Send the message via our own SMTP server.
s.send_message(msg)
print("DONE!")
s.quit()
