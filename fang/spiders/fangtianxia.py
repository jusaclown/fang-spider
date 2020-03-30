# -*- coding: utf-8 -*-
import scrapy
import re
from fang.items import NewHouseItem, ESFItem


class FangtianxiaSpider(scrapy.Spider):
    name = 'fangtianxia'
    allowed_domains = ['fang.com']
    start_urls = ['https://www.fang.com/SoufunFamily.htm']

    def parse(self, response):
        trs = response.xpath('//div[@class="outCont"]//tr')
        province = None
        for tr in trs:
            tds = tr.xpath(".//td[not(@class)]")
            province_td = tds[0]
            province_text = province_td.xpath('.//text()').get()
            province_text = re.sub(r"\s", "", province_text)
            if province_text:
                province = province_text

            if province == "其它" or province == "台湾":
                continue
            city_td = tds[1]
            city_links = city_td.xpath(".//a")
            for city_link in city_links:
                city = city_link.xpath(".//text()").get()
                city_url = city_link.xpath(".//@href").get()

                url_module = city_url.split(".", 1)
                if 'bj' in url_module[0]:
                    newshouse_url = "https://newhouse.fang.com/house/s/"
                    esf_url = "https://esf.fang.com/"
                else:
                    # 构建新房的url链接
                    newshouse_url = url_module[0] + '.newhouse.' + url_module[
                        1] + 'house/s'
                    # 构建二手房的url链接
                    esf_url = url_module[0] + '.esf.' + url_module[1]
                    # print("省份：", province,"城市：", city)
                    # print("城市链接：", city_url)
                    # print("新房：", newshouse_url)
                    # print("二手房", esf_url)
                yield scrapy.Request(url=newshouse_url,
                                     callback=self.parse_newhouse,
                                     meta={"info": (province, city)})
                yield scrapy.Request(url=esf_url, callback=self.parse_esf,
                                     meta={"info": (province, city)})

    def parse_newhouse(self, response):
        province, city = response.meta.get('info')
        lis = response.xpath(
            '//div[@id="newhouse_loupai_list"]/ul/li[not(@style)]')
        for li in lis:
            name = li.xpath('.//div[@class="nlcd_name"]/a/text()').get().strip()
            price = "".join(
                li.xpath('.//div[@class="nhouse_price"]//text()').getall())
            price = re.sub(r"\s|广告", "", price)
            house_type_list = li.xpath(
                './/div[contains(@class, "house_type")]//text()').getall()
            house_type_list = re.sub(r"\s", "", "".join(house_type_list)).split(
                '－')
            rooms = house_type_list[0]
            area = house_type_list[-1]
            address = li.xpath('.//div[@class="address"]/a/@title').get()
            district_text = "".join(
                li.xpath('.//div[@class="address"]/a//text()').getall())
            district = re.search(r".*\[(.+)\].*", district_text).group(1)
            sale = response.xpath(
                ".//div[@class='fangyuan pr']/span/text()").get()
            origin_url = response.xpath(
                ".//div[@class='nlcd_name']/a/@href").get()
            origin_url = response.urljoin(origin_url)
            item = NewHouseItem(province=province, city=city, name=name,
                                price=price, rooms=rooms, area=area,
                                address=address, district=district,
                                sale=sale, origin_url=origin_url)
            # print(name, price, rooms, area, address, district, sale, origin_url)
            yield item

        next_url = response.xpath(
            "//div[@class='page']//a[@class='next']/@href").get
        if next_url:
            yield scrapy.Request(url=response.urljoin(next_url),
                                 callback=self.parse_newhouse,
                                 meta={"info": (province, city)})

    def parse_esf(self, response):
        province, city = response.meta.get('info')
        dls = response.xpath(
            "//div[contains(@class, 'shop_list')]/dl[@dataflag!='bgcomare']")
        for dl in dls:
            item = ESFItem(province=province, city=city)
            item['name'] = dl.xpath(".//p[@class='add_shop']/a/@title").get()
            infos = dl.xpath(".//p[@class='tel_shop']//text()").getall()
            infos = list(map(lambda x: re.sub(r'\s|\|', '', x), infos))
            info = [x for x in infos if x != '']
            for info in infos:
                if "厅" in info:
                    item['rooms'] = info
                elif "㎡" in info:
                    item['area'] = info
                elif '层' in info:
                    item['floor'] = info
                elif "向" in info:
                    item['toward'] = info
                elif "年" in info:
                    item['year'] = info
                else:
                    item['username'] = info

            # item['rooms'] = info[0]
            # item['area'] = info[1]
            # item['floor'] = info[2]
            # item['toward'] = info[3]
            # item['year'] = info[4]
            # item['username'] = info[5]
            item['address'] = dl.xpath(
                ".//p[@class='add_shop']/span/text()").get()
            item['price'] = "".join(dl.xpath(
                ".//dd[@class='price_right']/span[1]//text()").getall())
            item['unit'] = dl.xpath(
                ".//dd[@class='price_right']/span[2]//text()").get()
            origin_url = dl.xpath(".//dd/h4[@class='clearfix']/a/@href").get()
            origin_url = response.urljoin(origin_url)
            item['origin_url'] = origin_url
            yield item

        next_page_url = None
        next_urls = response.xpath("//div[@id='list_D10_15']/p/a")
        for next_url in next_urls:
            if next_url.xpath('./text()').get() == "下一页":
                next_page_url = next_url.xpath("./@href").get()
                break
        if next_page_url:
            yield scrapy.Request(url=response.urljoin(next_page_url),
                                 callback=self.parse_esf,
                                 meta={"info": (province, city)})
