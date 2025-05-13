# Infinite Cloud Storage // Version 2.0
### currently broken/outdated
### Description
 - Infinite cloud storage utilises Discord servers for file storage. It also has a GUI to upload, download or delete files.
 - There are most likely still bugs, I will update over the coming weeks.
 - Inspired by DvorakDwarf's Infinite Storage Glitch. 

### Features
 - [x] Upload and download any file or folder, regardless of filesize, via a simple graphical interface.
 - [x] Folders are automatically compressed (.tar.bz2) for easy upload.
 - [x] Files and folders larger than the 25MB Discord limit are automatically split when uploaded.
 - [x] Files and folders that are split are automatically joined back together when downloaded. This process _shouldn't_ corrupt any data.
 - [x] Delete files from the record.
 - [x] Status indicator that can show download speed.
 - [x] Proper config GUI, so you don't have to enter in URLS directly into the code.
 - [ ] PLANNED: Upload speed indicator.
 - [ ] PLANNED: Encryption.

### Instructions & Requirements
 - You require a Discord Webhook (and the URL). Tutorial [here](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks).
 - You need to install the python library "discord-webhook" via `pip install discord-webhook` in your command line (unless you run via compiled executable).
 - You must enter the webhook URL into the "config" section of the application. Press the "config" button to access this.


___
norangeflame
