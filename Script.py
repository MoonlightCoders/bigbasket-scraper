from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup as bs
import requests
import shutil
import time
import os
import json
import re

def start_driver(headless=True):
    if not headless:
        return webdriver.Chrome(ChromeDriverManager().install())
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    return webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)


def save_image(image_link, save_dir):
    image_raw = requests.get(image_link, stream=True)
    filename = os.path.basename(image_link)
    img_dir = os.path.join(save_dir, filename)
    with open(img_dir, "wb") as out_file:
        shutil.copyfileobj(image_raw.raw, out_file)


def get_product_data(driver1, product, raw_data_file):
    link = product.find("div", {"qa": "product_name"}).find("a").attrs['href']
    full_link = 'https://www.bigbasket.com' + link
    print(full_link)

    additional_fields = ['About the product', 'Ingredients', 'Composition', 'Nutritional Facts', 'How to use', 'Benefits', 'Specification', 'Care Instructions', 'Variable Weight Policy', 'Storage & Uses', 'EAN Code']
    driver1.get(full_link)

    pack_sizes = []
    product_data = {}
    product_data['Product Code'] = link.split('/')[2]
    bread_crumbs = driver1.find_elements_by_class_name('_3WUR_')
    product_data['Master category'] = bread_crumbs[1].text
    product_data['Sub Category'] = bread_crumbs[2].text
    product_data['Micro category'] = bread_crumbs[3].text
    product_data['Brand'] = driver1.find_element_by_css_selector("a[context='brandlabel']").text
    product_data['Product name'] = bread_crumbs[4].text
    product_data['Pack Size'] = ''
    product_data['MRP'] = ''
    product_data['Selling price'] = ''

    additional_field_values = {}
    additions_infos = driver1.find_elements_by_class_name('_3ezVU')
    for index in range(len(additions_infos)) :
        additions_info = additions_infos[index]
        title = additions_info.find_element_by_class_name('_3LyVz').text
        description = additions_info.find_element_by_class_name('_26MFu').text
        additional_field_values[title] = description

        if title == 'Other Product Info' :
            additional_field_values['EAN Code'] = description.split('EAN Code: ')[1].split('\n')[0]

    for field in additional_fields :
        value = additional_field_values.get(field)
        product_data[field] = value or ''

    img = product.find("img")['src']
    # image_small = img.replace('/media/uploads/p/mm/', '/media/uploads/p/s/')
    image_large = img.replace('/media/uploads/p/s/', '/media/uploads/p/l/'). \
        replace('/media/uploads/p/mm/', '/media/uploads/p/l/')

    product_data['Image 1'] = image_large

    pack_sizes = list()
    element = driver1.find_elements_by_id('_2WW4W')
    if (element and element[0].text == 'Pack Sizes') :
        packs = driver1.find_elements_by_class_name("_2Z6Vt")

        for pack in packs :
            pack_sizes.append({
                'Pack Size': pack.find_elements_by_id('_3Yybm')[0].text,
                'MRP': pack.find_elements_by_id('tQ1Iy')[0].text.replace('Rs ', ''),
                'Selling price': pack.find_elements_by_id('_2j_7u')[0].text.replace('Rs ', ''),
            })
    else :
        selling_price = (driver1.find_element_by_css_selector("td[data-qa='productPrice']").text).replace('Rs ', '')
        mrp = selling_price
        element = driver1.find_elements_by_css_selector("td[class='_2ifWF']")
        if element and element[0] :
            mrp = element[0].text.replace('Rs ', '')

        pack_sizes.append({
            'Pack Size': '',
            'MRP': mrp,
            'Selling price': selling_price,
        })
    # packs

    # images = driver1.find_elements_by_class_name('_3oKVV')
    # for index in range(len(images)) :
    #     product_data['image_'+ str(index+1)] = images[index].get_attribute("src")
    # Brand = product.find("div", {"qa": "product_name"}).find("h6").text
    # Product = product.find("div", {"qa": "product_name"}).find("a").text
    # Quantity = product.find("span", {"data-bind": "label"}).text
    # Price = product.find("span", {"class": "discnt-price"}).text

    for pack in pack_sizes :
        product_data['Pack Size'] = pack['Pack Size']
        product_data['MRP'] = pack['MRP']
        product_data['Selling price'] = pack['Selling price']

        with open(raw_data_file, "a") as f:
            data = json.dumps(product_data)
            f.write(data + "\n")

    # try:
    #     save_image(image_small, os.path.join(OUTPUT_DIR, "images", "small"))
    #     save_image(image_large, os.path.join(OUTPUT_DIR, "images", "large"))
    # except Exception as e:
    #     print(e)


def dump_json(raw_data_file, out_data_file):
    with open(raw_data_file) as f:
        data = f.read().strip().split("\n")
    js_data = list(map(lambda x: json.loads(x), data))

    with open(out_data_file, "w") as f:
        json.dump(js_data, f, indent=2)


if __name__ == "__main__":
    driver = start_driver()

    DEBUG = True
    OUTPUT_DIR = "Output"
    out_data_file = os.path.join(OUTPUT_DIR, "data.json")
    delay = 8

    with open('links.txt', 'r') as f:
        url_list = f.read().split("\n")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    raw_data_file = os.path.join(OUTPUT_DIR, "raw_data.txt")
    with open(raw_data_file, "w") as f:
        pass

    for url in url_list:
        driver.get(url)
        print("Starting Download from: {}".format(url))

        time.sleep(delay)
        while True:
            try:
                driver.find_element_by_xpath("//button[@ng-click='vm.pagginator.showmorepage()']").click()
                time.sleep(2)
                # if DEBUG:
                #     print("Clicked Successfully")
            except Exception as e:
                if DEBUG:
                    print(e)
                break
        html = driver.execute_script("return document.documentElement.outerHTML")
        soup = bs(html, 'html.parser')
        products = soup.findAll("div", {"qa": "product"})

        rel_url = re.sub(r"/?.*", "", url)
        rel_url = rel_url.lstrip('https://www.bigbasket.com/pc/')

        ds_img = os.path.join(OUTPUT_DIR, 'images', 'large')
        dl_img = os.path.join(OUTPUT_DIR, 'images', 'small')

        if not os.path.exists(ds_img):
            os.makedirs(ds_img)
        if not os.path.exists(dl_img):
            os.makedirs(dl_img)

        for product in products:
            get_product_data(driver, product, raw_data_file)

        print("Downloaded all data from: ".format(url))

    print("Download finished from all the links.")
    dump_json(raw_data_file, out_data_file)
    print("JSON file saved as {}".format(raw_data_file))

    driver.quit()
