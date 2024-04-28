import os
from typing import Final
from telegram import Update
from telegram.ext import Updater, Application, CommandHandler, MessageHandler, filters, ContextTypes
from googleapiclient.discovery import build
from sppcredentials import bot_key, api_key # custom library with your parameters
import html
import datetime

# Telegram Bot Token
TOKEN: Final = bot_key
BOT_USERNAME: Final = '@sppyt_bot'

# Init YouTube API 
YOUTUBE_API_KEY = api_key
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# ===========================================
# Commands
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to the YouTube Search Bot! Message bot to search for youtube videos. Use /help to understand what you can do.')

async def setfilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    options = ['viewCount', 'date', 'rating', 'relevance']
    if len(context.args) == 0:
        await update.message.reply_text('Please provide a filter option. Example: /setfilter viewCount. Available options are: viewCount, date, rating, relevance')
    elif context.args[0] not in options: 
        await update.message.reply_text('Filter not set. Please choose from the following options:\n' + ', '.join(options))
    else:
        # Save the filter option to the user's context
        context.user_data['filter'] = context.args[0]
        await update.message.reply_text(f'Filter set to "{context.args[0]}"')

async def setamount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text('Please provide the number of results you want to see. Example: /setamount 7')
    else:
        try:
            amount = int(context.args[0])
            if amount <= 0:
                await update.message.reply_text('Please provide a positive number.')
            else:
                # Save the amount to the user's context
                context.user_data['amount'] = amount
                await update.message.reply_text(f'Amount of results set to {amount}')
        except ValueError:
            await update.message.reply_text('Please provide a valid number.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Just message me what you want to search for on Youtube and I will give you a couple of links to videos you might consider interesting. \n\nYou can control me by sending these commands: \n/setfilter - sets filter for a query. Searching by View Count is enabled by defaut. Options are: viewCount, date, rating, relevance \n/setamount - sets how much results you will get. Default is 5')

# ===========================================
# Handler
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type 
    query = update.message.text
    print(f'User ({update.message.chat.id}) in {message_type}: "{query}"')

    context.user_data['query'] = query
    if 'results_sent' not in context.user_data:
        context.user_data['results_sent'] = 0

    # Check if the user has set a filter
    if 'filter' in context.user_data:
        filter_option = context.user_data['filter']
    else:
        filter_option = 'viewCount'

    # Check if the user has set the amount
    if 'amount' in context.user_data:
        amount = context.user_data['amount']
    else:
        amount = 5
        context.user_data['amount'] = amount

    videos = search_videos(query, filter_option, amount)
    message = ""
    for i, video in enumerate(videos, 1):
        if filter_option == 'viewCount':
            message += f"{i}. {video['title']} \nViews: {video['view_count']} \nLink: {video['url']}\n"
        elif filter_option == 'date':
            message += f"{i}. {video['title']} \nPublished At {video['published_at']} \nLink: {video['url']}\n"
        else:
            message += f"{i}. {video['title']} \nLink: {video['url']}\n"
    await update.message.reply_text(message)

# Auxiliary function to search YouTube videos
def search_videos(query, filter_option, amount):
    search_response = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        order=filter_option,
        maxResults=amount
    ).execute()

    videos = []
    for item in search_response['items']:
        video_id = item['id']['videoId']
        video_response = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        ).execute()
        view_count = video_response['items'][0]['statistics']['viewCount'] if 'viewCount' in video_response['items'][0]['statistics'] else 'Not available'
        published_at = datetime.datetime.strptime(item['snippet']['publishedAt'], '%Y-%m-%dT%H:%M:%SZ').strftime('%Y.%m.%d')

        videos.append({
            'title': html.unescape(item['snippet']['title']),
            'url': f'https://www.youtube.com/watch?v={item["id"]["videoId"]}',
            'view_count': view_count,
            'published_at': published_at
        })

    return videos

# ===========================================
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

# ===========================================
# MAIN
if __name__ == '__main__':
    print('Starting bot...')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('setfilter', setfilter_command))
    app.add_handler(CommandHandler('setamount', setamount_command))
    app.add_handler(CommandHandler('help', help_command))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Errors
    app.add_error_handler(error)

    # Polls the bot
    print('Polling...')
    app.run_polling(poll_interval=3)