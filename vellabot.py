#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import praw
import prawcore
import schedule
import time
import threading
from pymongo import MongoClient
import random
import yaml
import requests
import pendulum
import discord



trigger = "!vellabot"


class vellabot(mp.Process):
    def __init__(self, connection, reddit, webhook, comment):
        self.CONNECTION_STRING = connection
        self.reddit = reddit
        self.SUBREDDIT = self.reddit.subreddit("indiasocial")
        self.comment = comment
        self.MClient = MongoClient(self.CONNECTION_STRING)
        self.db = self.MClient["2024"]
        self.wikiLink = "\n\n[^(How to use.)](https://reddit.com/r/indiasocial/w/vellabot/)"
        self.webhook = webhook


        self.months = [
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december"
        ]

        self.memes = [
        '### Shaddap 3%', '### nirlajj tu fir aa gya', '### Teri Keh Ke Lunga',
        '### Behti hai nadi girta hai jharna,\n\n ee meowdalchod apna kaam karna',
        '### pel dunga'
        ]

        self.optoutReplies = [
        '### Ab aapka username bas dil mai aayega, mere replies mai nhi',
        '### Accha chalta huu, duaaoon mai yaad rakha, mujhe dekhte hi upvote pe haath rakhna',
        '### Sorry ji ab hum karenge aapko ignore, itni jaldi kyo ho gye aap humse bore'
        ]

        self.optinReplies = [
        '### Tera mujhse tha pehle ka naata koi, yuhi thodi wapas bulata koi',
        '### Dooba Dooba rehta tha yaadon mei teri, wapas aa gya hu ab replies mai teri',
        '### koi chahe, chahta rhe, mushil hai humko bhulana\n\n ### hum aa gye, andaaz leke purana'
        ]

        self.verdicts = {
            (121, 201): "Legendary Vella",
            (101, 121): "Expert Vella",
            (81, 101): "Bohot Vella",
            (61, 81): "Vella",
            (41, 61): "Thodusa Vella",
            (21, 41): "Biji",
            (1, 21): "Very Biji",
            (0, 0): 'Lmao ded'
        }

        self.query_month = [i[:3] for i in self.months]

    def logit(self, logMessage):
        pnow = pendulum.now("Asia/Kolkata")
        when = pnow.format('H:m:s - D MMM YY ')
        logMessage = f"{when} {logMessage}"
        try:
            embed = discord.Embed(description = f"{logMessage}",color=0x32cd32)
            self.webhook.send(embed = embed)
        except:
            return
    
    def Entry(self):
        try:
            month = ''
            post = self.reddit.submission(id=self.comment.submission).title
            if post.find("Random Discussion Thread") != -1:
                for m in self.months:
                    if post.lower().find(m) != -1:
                        user = str(self.comment.author)
                        month = m
                        break
                if len(month)>1:
                    col = self.db[month]
                    tally = 1
                    if col.count_documents({'user': user}) > 0:
                        data = col.find_one( { "user": user } )
                        col.delete_one({'user': user})
                        tally = data['comments']+1
                    col.insert_one({'user': user, 'comments':tally})
        except Exception as e:
            self.logit(f" -- Error in Entry Method: {e}")
            return
    
    def replyUser(self, message):
        if self.comment and message:
            message += self.wikiLink
            try:
                l = self.comment.reply(body=message)
                l.disable_inbox_replies()
            except Exception as e:
                self.logit(f" -- Error While commenting | Error : {e}")
                return
            
    def topInMonth(self, text):
        if len(text) > 1 and (text[1].lower() in self.query_month):
            message = 'Top 5 Vellas in '+ text[1] +': \n\n'
            message += 'User|Comments Count\n:-:|:-:\n'
            for m in self.months:
                if text[1][:3].lower() == m[:3]:
                    ignore_collection = self.db["ignore"]
                    users_to_ignore = [user['_id'] for user in ignore_collection.find()]
                    data = self.db[m].find({"user": {"$nin": users_to_ignore}}).sort("comments", -1).limit(5)
            for i in data:
                message += i['user'] + '|' + str(i['comments']) + '\n'
            self.replyUser(message)
    
    def userData(self, text, total_days):
        message = 'Month|Comments Count\n:-:|:-:\n'
        user = [str(self.comment.author).lower()]
        if len(text) > 1:
            user = text[1].lower().split('+')
            if 'vellabot' in user:
                message = random.choices(self.memes, k=1)
            self.replyUser(message)
            return
        if self.db['ignore'].count_documents({'_id': {"$in": user}}) > 0:
            return
        total_comments = 0

        ## Get current month
        current_month = 0
        for i in range(0, 12):
            if self.db[self.months[i]].count_documents({}) == 0:
                break
            current_month = i
        ## Get current month

        count = 0
        for i in range(0, current_month-2):
            data = self.db[self.months[i]].find()
            for entry in data:
                if entry['user'].lower() in user:
                    count += entry['comments']
        if current_month - 3 >= 0:
            message += 'Till ' + self.months[current_month-3].capitalize()[:3] + '|' + str(count) + '\n'

        for i in range(current_month-2, current_month+1):
            if i < 0:
                continue
            data = self.db[self.months[i]].find()
            count = 0
            for entry in data:
                if entry['user'].lower() in user:
                    count += entry['comments']
            total_comments = count
            message += self.months[i].capitalize()[:3] + '|' + str(count) + '\n'

        average = total_comments // total_days
        verdict = 'Mr/Mrs Vellaverse'
        for range_, result in self.verdicts.items():
            lower, upper = range_
            if lower <= average <= upper:
                verdict = result
                break
        message += '\nAvg no of Comments/Day made by ' + user[0] + ' in ISO LNRDT in this month: ' + str(average) + '\n\nVerdict: ' + verdict
        self.replyUser(message)

    
    
    def run(self):
        post = self.reddit.submission(id=self.comment.submission).title
        if self.comment.body.lower().find(trigger) != -1:
            text = self.comment.body
            text = text[self.comment.body.lower().find(trigger):].split(' ')

        total_days = 1
        words = post.split(' ')
        for word in words:
            try:
                total_days = int(word)
                break
            except:
                continue

        self.topInMonth(text)
        self.userData(text, total_days)

