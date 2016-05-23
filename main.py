import os
import re
import time
import json
import html
import contextlib
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException


class FirefoxContext:

    def __init__(self):
        self.driver = webdriver.Firefox()

    def __enter__(self):
        return self.driver

    def __exit__(self, *exec):
        self.driver.close()


class PhantomJSContext:
    template = """<html><head><meta charset="UTF-8" /></head><body>{}</body></html>"""
    template_file = "temp.html"

    def __init__(self, data, is_url=False):
        self.driver = webdriver.PhantomJS()
        if is_url:
            self.driver.get(data)
        else:
            with open(self.template_file, 'w+', encoding='utf-8') as f:
                f.writelines(self.template.format(data))
            self.driver.get(os.path.join(self.template_file))
            with contextlib.suppress(FileNotFoundError):
                os.remove(self.template_file)

    def __enter__(self):
        return self.driver

    def __exit__(self, *exec):
        self.driver.close()


class BasePage:

    def __init__(self, driver):
        self.driver = driver


class HomePage(BasePage):
    start_url = "http://www.pagespro.com/"
    begin_title = "Annuaire"

    def run(self):
        self.driver.get(self.start_url)

    def is_load(self):
        if self.begin_title not in self.driver.title:
            raise Exception("HomePage not loaded")

    def launch_search(self, keyword):
        # "//input[@name='continue'][@type='button']"
        searchinput = self.driver.find_element_by_id("activ_exp")
        searchinput.send_keys(keyword)
        searchinput.send_keys(Keys.RETURN)
        self.driver.implicitly_wait(10)
        selectall = self.driver.find_element_by_xpath("//a[@class='orangetitle'][@onclick='ToutSelActiv(true)']")
        selectall.click()
        self.driver.implicitly_wait(3)
        gosearch = self.driver.find_element_by_xpath("//a[@class='orangetitle'][@onmousedown='ValideChoixActiv()']")
        gosearch.click()
        self.driver.implicitly_wait(10)
        time.sleep(2)


class ResultsSearchPage(BasePage):

    max_res_by_page = 10

    def __init__(self, driver):
        super().__init__(driver)
        with contextlib.suppress(FileNotFoundError):
            os.remove(os.path.join("company.txt"))
            os.remove(os.path.join("error.txt"))

    def results_in(self):
        # <b class="total_responses_nr">2673 réponses</b>
        result_text = self.driver.find_element_by_class_name("total_responses_nr").text.encode(errors='replace')
        pattern = b'\xe2\x80\x93\s*(\d+)\s*r\xc3\xa9ponses\s*sur\s*l\xe2\x80\x99ensemble\s*de\s*l\xe2\x80\x99activit\xc3\xa9\s*\xe2\x80\x93'
        num_result = re.compile(pattern)
        num = num_result.search(result_text)
        if not num:
            raise Exception("No results found")
        self._num_result = int(num.group(1))
        _ = self._num_result / self.max_res_by_page
        if isinstance(_, float):
            self._num_foward_click = int(_)
        else:
            self._num_foward_click = int(_) - 1

    def extract_results(self):
        self.driver.implicitly_wait(1)
        items = self.driver.find_elements_by_xpath("//div[@itemtype='http://data-vocabulary.org/Organization']")
        optional_fields_item = (
            ('phones', self._extract_phones),
            # ('web_infos', self._extract_web_infos),
            # ('specifities', self._extract_specifities),
            # ('manageo_datas', self._extract_manageo_datas),
        )
        for item in items:
            with PhantomJSContext(item.get_attribute('outerHTML')) as itemdriver:
                cp_pagespro = {
                    'companyname': itemdriver.find_element_by_xpath("//span[@itemprop='name']").text,
                    'street-address': itemdriver.find_element_by_xpath("//span[@itemprop='street-address']").text,
                    'postal-code': itemdriver.find_element_by_xpath("//span[@itemprop='postal-code']").text,
                    'locality': itemdriver.find_element_by_xpath("//span[@itemprop='locality']").text
                }
                try:
                    cp_pagespro['firstdesc'] = itemdriver.find_element_by_xpath("//div[@class='results_inset_desc']").text
                    cp_pagespro['seconddesc'] = itemdriver.find_element_by_xpath("//span[@class='speciality_link']//div[@class='puce_domaine']").text
                except NoSuchElementException:
                    cp_pagespro['firstdesc'] = itemdriver.find_element_by_xpath("//span[@class='speciality_link']//div[@class='puce_domaine']").text
                    cp_pagespro['seconddesc'] = None
                for (field, func) in optional_fields_item:
                    func(itemdriver)

    def _next_results_page(self):
        pass

    def _extract_phones(self, driver):
        list_regex = (
            ("tel", re.compile(r'.*(t[ée]l).*')),
            ("fax", re.compile(r'.*(fax).*')),
            ("gsm", re.compile(r'.*(mobile).*'))
        )
        list_strong = driver.find_elements_by_xpath("//div[@class='coordonnees']//div[@class='tel float-right']//strong")
        phones = driver.find_elements_by_xpath("//div[@class='coordonnees']//div[@class='tel float-right']//span[@itemprop='tel']")
        phones_output = {
            "tel": None, "fax": None, "gsm": None
        }
        if len(phones) != len(list_strong):
            raise Exception("len phones != len list_strong may trained a problem of correlation of phones")
        for (i, strong) in enumerate(list_strong):
            for (tag, regex) in list_regex:
                match = regex.search(strong.text)
                if match:
                    if not isinstance(phones_output[tag], list):
                        phones_output[tag] = list()
                    phones_output[tag].append(phones[i].text.strip())
                    break
        try:
            if driver.find_element_by_xpath("//div[@class='coordonnees']//a[contains(@class,'l_coord')]"):
                other_phones = driver.find_elements_by_xpath("//div[@class='coordonnees']//table//tr")
                list_regex_add_phones = (
                    ("tel", re.compile(r'.*\n.*\n.*\n\s+t[ée]l.*\n.*\n.*\n.*\n.*\n\s+(?P<tel>.*)</span>')),
                    ("fax", re.compile(r'.*\n.*\n.*\n\s+fax.*\n.*\n.*\n.*\n.*\n\s+(?P<fax>.*)</span>')),
                    ("gsm", re.compile(r'.*\n.*\n.*\n\s+mobile.*\n.*\n.*\n.*\n.*\n\s+(?P<gsm>.*)</span>')),
                )
                for other_phone in other_phones:
                    for (tag, regex) in list_regex_add_phones:
                        match = regex.search(other_phone.get_attribute('outerHTML'))
                        if match:
                            if not isinstance(phones_output[tag], list):
                                phones_output[tag] = list()
                            phones_output[tag].append(html.unescape(match.group(tag)).strip().replace('\xa0', ' '))
                            phones_output[tag] = list(set(phones_output[tag]))
                            break
        except NoSuchElementException:
            pass
        return phones_output

    def _extract_web_infos(self, driver):
        list_regex = (
            ("siteweb", re.compile(r'.*(Site\s+Web\s+:).*')),
            ("email", re.compile(r'.*(E-mail\s+:).*'))
        )
        list_b = driver.find_elements_by_xpath("//div[@class='coordonnees_web']//b")
        web_infos = driver.find_elements_by_xpath("//div[@class='coordonnees_web']//a")
        web_infos_output = {
            "siteweb": None, "email": None
        }
        if len(web_infos) != len(list_b):
            raise Exception("len web_infos != len list_b may trained a problem of correlation of web_infos")
        for (i, b) in enumerate(list_b):
            for (tag, regex) in list_regex:
                match = regex.search(b.text)
                if match:
                    if not isinstance(web_infos_output[tag], list):
                        web_infos_output[tag] = list()
                    web_infos_output[tag].append(web_infos[i].text.strip())
                    break
        return web_infos_output

    def _extract_specifities(self, driver):
        list_regex = (
            ("emp", re.compile(r'<div.*>.*\n.*Effectif.*?(?P<minemp>\d+)\s+(?:à|ou)\s+(?P<maxemp>\d+)')),
            ("siret", re.compile(r'<div.*>.*\n.*Siret.*?(?P<siret>\d+)')),
            ("codeact", re.compile(r".*&lt;strong&gt;(?P<code>.+)&lt;/strong&gt;\s+:\s+(?P<codedesc>.+)',null", re.M))
        )
        specifities_output = {
            "minemp": 0, "maxemp": 0, "siret": None, "codeact": {"code": None, "codedesc": None}
        }
        try:
            if driver.find_element_by_xpath("//div[@class='results_part4']"):
                list_specifities = driver.find_elements_by_xpath("//div[@class='results_part4']/div/div")
                for specifie in list_specifities:
                    for (tag, regex) in list_regex:
                        match = regex.search(specifie.get_attribute('outerHTML'))
                        if match and tag == "emp":
                            specifities_output['minemp'] = int(match.group('minemp'))
                            specifities_output['maxemp'] = int(match.group('maxemp'))
                            break
                        elif match and tag == "siret":
                            specifities_output['siret'] = match.group('siret')
                            break
                        elif match and tag == "codeact":
                            specifities_output['codeact']['code'] = match.group('code')
                            specifities_output['codeact']['codedesc'] = match.group('codedesc')
                            break
        except NoSuchElementException:
            pass
        return specifities_output

    def _extract_manageo_datas(self, driver):
        manageo_output = {
            "companyname": None, "companyaddress": None, "rcs": None,
            "activity": None, "birthday": None, "legalform": None,
            "capital": None, "ceo": None, "nb_establishment": None, "datedatas": None,
            "minemp": 0, "maxemp": 0, "salesrevenu": None, "gain": None
        }
        list_regex_h = (
            ('companyname', re.compile(r'<p.*>.*\n.*\n.*>(?P<companyname>.*)</a>')),
            ('companyaddress', re.compile(r'<p.*>.*\n.*Si.*\n\s+(?P<companyaddress>.*)</p>')),
            ('rcs', re.compile(r'<p.*>.*\n.*RCS.*\n\s+(?P<rcs>.*)</p>')),
            ('activity', re.compile(r'<p.*>.*\n.*Act.*\n\s+(?P<code>.*)&nb.*\n.*>(?P<codedesc>.*)<')),
            ('birthday', re.compile(r'<p.*>.*\n.*Date.*\n\s+(?P<birthday>.*)</p>')),
            ('legalform', re.compile(r'<p.*>.*\n.*Forme.*\n\s+(?P<legalform>.*)</p>')),
            ('capital', re.compile(r'<p.*>.*\n.*Capital.*\n\s+(?P<capital>.*)</p>')),
            ('ceo', re.compile(r'<p.*>.*\n.*Diri.*\n\s+<a.*>(.*)</a>(.*)</p>')),
            ('nb_establishment', re.compile('<p.*>.*\n.*Eta.*\n\s+(?P<nb_establishment>.*)</p>'))
        )
        list_regex_b = (
            ('emp', re.compile(r'<p.*>.*\n.*\n.*?(?P<minemp>\d+)\s+(?:à|ou)\s+(?P<maxemp>\d+)')),
            ('salesrevenu', re.compile(r'<p.*>.*\n.*Chi.*\n.*>(?P<salesrevenu>.*)</a>')),
            ('gain', re.compile(r'<p.*>.*\n.*Ré.*span>\n\s+(?P<gain>.*)</p>'))
        )
        try:
            is_exist = driver.find_element_by_xpath("//a[@class='icon_infos']")
            if is_exist:
                regex = re.compile(r'results_part1_(?P<idresult>\d+)')
                id_icon = driver.find_element_by_xpath("//div[@class='results_part1']").get_attribute('id')
                match = regex.search(id_icon)
                action = self.driver.find_element_by_xpath("//a[@id='icon_infos_{}']".format(match.group('idresult')))
                action.click()
                self.driver.implicitly_wait(5)
                frame = self.driver.find_element_by_xpath("//div[@id='results_part8_{}']//iframe".format(match.group('idresult')))
                with PhantomJSContext(frame.get_attribute('src'), is_url=True) as frame_driver:
                    bh_elements = frame_driver.find_elements_by_xpath("//div[@id='blocHaut']//div[@class='bloc1']//p")
                    for bh_element in bh_elements:
                        for (tag, regex) in list_regex_h:
                            match = regex.search(bh_element.get_attribute('outerHTML'))
                            if match and tag == 'nb_establishment':
                                manageo_output[tag] = int(match.group('nb_establishment'))
                                break
                            elif match:
                                manageo_output[tag] = html.unescape(" ".join(match.groups())).replace('\xa0', ' ')
                                break
                    try:
                        if frame_driver.find_element_by_xpath("//div[@id='blocBas']"):
                            manageo_output['datedatas'] = frame_driver.find_element_by_xpath("//div[@id='blocBas']/span/span").text
                            bb_elements = frame_driver.find_elements_by_xpath("//div[@id='blocBas']//p")
                            for bb_element in bb_elements:
                                for (tag, regex) in list_regex_b:
                                    match = regex.search(bb_element.get_attribute('outerHTML'))
                                    if match and tag == 'emp':
                                        manageo_output['minemp'] = int(match.group('minemp'))
                                        manageo_output['maxemp'] = int(match.group('maxemp'))
                                        break
                                    elif match:
                                        manageo_output[tag] = html.unescape(match.group(tag)).replace('\xa0', ' ')
                                        break
                    except NoSuchElementException:
                        pass
        except NoSuchElementException:
            pass
        return {'manageo': manageo_output}


def main():
    with open("results.html", encoding="utf-8") as f:
            data = f.read()
    with PhantomJSContext(data) as driver:
        # home = HomePage(driver)
        # home.run()
        # home.is_load()
        # home.launch_search("BTP")
        results_search_page = ResultsSearchPage(driver)
        results_search_page.results_in()
        results_search_page.extract_results()

if __name__ == '__main__':
    main()
