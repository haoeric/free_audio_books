import os
import re
import time
import json
import uuid
import boto3
import shlex
import shutil
import argparse
import requests
import subprocess
import youtube_dl
from decimal import Decimal as D
from bs4 import BeautifulSoup as bs
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr


# aws S3
s3 = boto3.resource('s3')
s3_bucket_name = "haoeric-audio-books"
# dynamodb tables
dynamodb = boto3.resource('dynamodb', region_name="ap-southeast-2")
dynamondb_table_name = "free_audio_books"
free_audio_table = dynamodb.Table(dynamondb_table_name)
# global var to store video urls
video_url_list = []


def dynamodb_create(table_name, hash_key_name, range_key_name,
                    hash_key_type, range_key_type,
                    read_capacity_unit, write_capacity_unit):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {
                'AttributeName': hash_key_name,
                'KeyType': 'HASH'
            },
            {
                'AttributeName': range_key_name,
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': hash_key_name,
                'AttributeType': hash_key_type
            },
            {
                'AttributeName': range_key_name,
                'AttributeType': range_key_type
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': read_capacity_unit,
            'WriteCapacityUnits': write_capacity_unit
        }
    )
    # Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    # Print out some data about the table.
    print(table.item_count)


# create dynamoDB table (run once only)
# dynamodb_create(table_name = dynamondb_table_name,
#                 hash_key_name = "url",
#                 hash_key_type = "S",
#                 range_key_name = "keyword",
#                 range_key_type = "S",
#                 read_capacity_unit = 5,
#                 write_capacity_unit = 5)


def dynamodb_exists_check(hash_key, table):
    try:
        item = table.query(KeyConditionExpression=Key('url').eq(hash_key))['Items']
    except:
        item = []
    if len(item) == 0:
        item = None
    return item


# See http://docs.python.org/2/library/json.html
# Extending JSONEncoder:
class DecimalEncoder2(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, D):
            return float(obj)
        return json.JSONEncoder.default(self, obj)



def delete_working_dir(working_dir):
    try:
        shutil.rmtree(working_dir)
    except Exception as e:
        print ('Can\'t delete %s' % working_dir)



def youtube_link_scrawler(base_link="https://www.youtube.com/results?search_query=", query_string=""):
    if query_string == "":
        query_link = base_link
    else:
        query_link = base_link + query_string
    # get serach page html
    search_return = requests.get(query_link)
    search_parser = bs(search_return.text, 'html.parser')
    # find all links of returned videos
    vids = search_parser.findAll('a', attrs={'class': 'yt-uix-tile-link'})
    for v in vids:
        tmp = 'https://www.youtube.com' + v['href']
        video_url_list.append(tmp)
    # get the link for next page
    buttons = search_parser.findAll('a', attrs={'class': "yt-uix-button vve-check yt-uix-sessionlink yt-uix-button-default yt-uix-button-size-default"})
    if len(buttons) > 0:
        nextPagelink = "https://www.youtube.com" + buttons[-1]['href']
        # continue crawl next page
        print("Crawl page: " + nextPagelink)
        youtube_link_scrawler(base_link=nextPagelink)



def youtube_video_downloader(keyword, video_url, local_path, s3_path):
    print(">>")
    print(">>")
    print("----------------------------------")
    print("[%s] - Processing link: %s" % (keyword, video_url))
    record_meta = {"url": video_url, "keyword": keyword}
    # check existence, create new record in dynamoDB if it's new
    exist_item = dynamodb_exists_check(video_url, free_audio_table)
    if exist_item is None:
        print(">>>>write url to dynamondb")
        # convert all float to decimal
        res_str = json.dumps(record_meta, cls=DecimalEncoder2)
        res_json = json.loads(res_str, parse_float=D)
        free_audio_table.put_item(Item=res_json)
    else:
        if 's3_loc' in exist_item[0]:
            print(">>>>item already in dynamondb, skip!")
            return None
    print(">>>>download audio file")
    uid = str(uuid.uuid1())
    local_path = os.path.join(local_path, uid)
    if not os.path.exists(local_path):
        os.makedirs(local_path)

    ydl_opts = {'format': 'bestaudio/best',
                'outtmpl': os.path.join(local_path, '%(title)s.%(ext)s')}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

    print(">>>>check downloaded files")
    downloaded_files = os.listdir(local_path)
    if len(downloaded_files) > 0:
        print(">>>>audio files have been successfully downloaded") 
        for file_i in downloaded_files:
            in_audio_file = os.path.join(local_path, file_i)
            print(in_audio_file)
            try:
                title = os.path.basename(in_audio_file)      # remove search keyword
                title = re.sub(keyword, '', title, flags=re.IGNORECASE)    # remove special symbol
                title = re.sub('[!@#$\(\)\[\]]', '', title)          # remove (...)
                title = re.sub('\([\w\s]+\)', '', title)     # remove suffix, like .webm
                title = re.sub('\..+$', '', title)           # remove leading and trailing empty space
                title = title.strip()                        # replace all other empty space with '-'
                title = re.sub('\s+', '_', title).lower()    # all to lower cases
                checked_in_audio_file = os.path.join(local_path, re.sub("^.+\.", title+".", in_audio_file))
                os.rename(in_audio_file, checked_in_audio_file)
                print(checked_in_audio_file)
                print(">>>>  book title: " + title) 
                print(">>>>convert audio to mp3 format") 
                out_origin_mp3_file = os.path.join(local_path, title + "_origin.mp3")
                ffmpeg_cmd = "ffmpeg -i %s %s" % (checked_in_audio_file, out_origin_mp3_file)
                print(ffmpeg_cmd)
                subprocess.call(ffmpeg_cmd, shell=True)
                print(">>>>compress mp3 to Bitrate = 32 kbps")
                out_compressed_mp3_file = os.path.join(local_path, title + ".mp3")
                lame_cmd = "lame -b 32 %s %s" % (out_origin_mp3_file, out_compressed_mp3_file)
                print(lame_cmd)
                subprocess.call(lame_cmd, shell=True)
                print(">>>>upload compressed mp3 file to s3") 
                s3.meta.client.upload_file(out_compressed_mp3_file, s3_bucket_name, 
                                           os.path.join(keyword, title + ".mp3"))
                print(">>>>update to dynamoDB record with complete information")  
                record_meta['keyword'] = record_meta['keyword'] + "-" + title
                record_meta['title'] = title
                record_meta['s3_loc'] = os.path.join(s3_bucket_name, keyword, title + ".mp3")
                # convert all float to decimal
                res_str = json.dumps(record_meta, cls=DecimalEncoder2)
                res_json = json.loads(res_str, parse_float=D)
                free_audio_table.put_item(Item=res_json)
            except Exception as e:
                print("failed to processing video - " + in_audio_file)
                print('Error message: '+ str(e))  
    ## clear data
    delete_working_dir(local_path)
    


def main():
    parser = argparse.ArgumentParser('audio_books_crawler')
    parser.add_argument('--query_string', default='audiobook|audio book',
                        type=str, help='key words for youtube query, concatenate using | if want search multiple keywords')
    parser.add_argument('--bucket_name', default='haoeric-audio-books',
                        type=str, help='S3 bucket where store the audio files')
    parser.add_argument('--working_dir', type=str,
                        help='code working directory', default='/scratch')
    args = parser.parse_args()

    keywords = args.query_string.split("|")
    if len(keywords) > 0:
        for keyword in keywords:
            print("Searching videos with query keyword: " + keyword)
            youtube_link_scrawler(query_string=keyword)
            print("  --in total found " + str(len(video_url_list)) + " videos")
            for video_url in video_url_list:
                try:
                    youtube_video_downloader(keyword, video_url, args.working_dir, args.bucket_name)
                except Exception as e:
                    print("failed to crawl video - " + video_url)
                    print('Error message: '+ str(e))   
            # clear video_url_list
            video_url_list.clear()
    return None



if __name__ == '__main__':
    main()
