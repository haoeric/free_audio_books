
# Daily Digest in Chinese

![](/logo/skill_page.png)

This Alexa skill broadcasts the latest Chinese news from [ReadHub](https://readhub.me/). Enable this skill on your [Echo](https://www.amazon.com/all-new-amazon-echo-speaker-with-wifi-alexa-dark-charcoal/dp/B06XCM9LJ4) device to help you stay tuned with the latest technology news.

Please be aware that the news is broadcast in Chinese.


If you have an echo product, you can [enable this skill](https://www.bioconductor.org/packages/cytofkit/) to try and test, or play with it [here](https://echosim.io/) if you don't! 

Welcome feedback and suggestions!


# How is This Made

## 1. Create a Spider to crawl the news from readhub.com

### Creating a scrapy project

```
scrapy startproject chinanews_crawler
```

### Create our spider class

> Spiders are classes that you define and that Scrapy uses to scrape information from a website (or a group of websites). They must subclass scrapy.Spider and define the initial requests to make

create a file named `readhub_spider.py` under `readhub_news_crawler/spiders/` with following codes:


```
import scrapy
import time

class newsItem(scrapy.Item):
    id = scrapy.Field()
    date = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    source = scrapy.Field()
    
class readhubSpider(scrapy.Spider):
    name = "readhub"
    start_urls = ['https://readhub.me']

    def parse(self, response):
        item = newsItem()
        all_news = response.xpath('//*[@id="itemList"]/div')
        for news in all_news:
            date = time.strftime("%d-%m-%Y")
            title = news.css('div.topicItem___3YVLI h2.topicTitle___1M353 span.content___2vSS6::text').extract()
            links = news.css('div.articleItem___2P-7U a.articleTitle___3zy5I::attr(href)').extract()
            
            item['id'] = date + "-" + str(hash(title[0]))
            item['date'] = date
            item['title'] = title
            item['content'] = news.css('div.summary___1i4y3 div.bp-pure___3xB_W::text').extract()
            item['source'] = ";".join(links)
            yield item
            
```

### Put our spider to work

Go to the project’s top level directory and run:

```
scrapy crawl readhub -t csv -o "readhub.csv" --loglevel=INFO
```

## 2. install keda xunfei

Download `xunfei_tts` from [xfyun](https://www.xfyun.cn/services/online_tts)

```
bash 64bit_make.sh
```

paramter set up and [configuration](http://bbs.xfyun.cn/forum.php?mod=viewthread&tid=15340)

## 3. install lame

download from [lame v3.100](https://sourceforge.net/projects/lame/files/lame/3.100/)

```
make -f Makefile.unix
```

## 4. wrap up in a container and push to AWS ECS

```
## docker test
docker run -it --entrypoint /bin/bash daily_digest_alexa
```

## 5. Configure AWS Batch Environment


### Create IAM roles 

Create IAM roles that provide service permissions using following script or manually through AWS IAM console

```
aws cloudformation create-stack --template-body file:////Users/chenhao/GitProject/Alexa-skill-Daily-Digest/batch/aws_role_setup.yaml --stack-name iam --capabilities CAPABILITY_NAMED_IAM
```

NOTE: for `ecsInstanceRole`, using policy `AmazonEC2ContainerServiceforEC2Role-version4` instead of the default version 5(some problem existed)

### Build a custom EC2 image

modify the default Amazon `ECS-Optimized Amazon Linux AMI` from AWS marketplace in the following ways:

- Attach a 50 GB scratch volume to `/dev/sdb`
- Mount the scratch volume to `/docker_scratch` by modifying `/etcfstab`. (After your instance has launched, record the IP address and then SSH into the instance, run the following code)

```
sudo yum -y update
# Check the device name
sudo fdisk -l
# Make directory to where you want to mount the volume
sudo mkdir /docker_scratch
# Create filesystem on your volume 
sudo mkfs.ext4 /dev/xvdb
# Mount volume
sudo mount -t ext4 /dev/xvdb /docker_scratch
# If you want to preserve the mount after e.g. a restart, open /etc/fstab and add the mount to it
## note the following path /dev/xvdb1 may change case by case
echo "/dev/xvdb1 /docker_scratch auto noatime 0 0" | sudo tee -a /etc/fstab
# Make sure nothing is wrong with fstab by mounting all
sudo mount -a

sudo chmod 777 /docker_scratch
```

### Create batch computing environment, queue, and rejister job definition

```
bash ./batch/batch_env_queue_job.sh
```


### create lambda function and cloudwatch event





## 6. Build Alexa APP
