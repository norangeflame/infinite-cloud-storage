###Unlimited Cloud Storage via Discord###
#----------------------------------------
#Usage:
# - Add your token to the "token" variable
# - Add the channel ID to store files to the "channelId" variable
# - Add the webhook URL to both the "wbhkurl" variable
# - NOTE: make sure you don't use the file storing channel for general messages. This will cause longer download times.
# - NOTE: make sure the Webhook is set to send messages to the file storing channel. A mismatch in your channelId and the channel
#         that the webhook is set to will break the cloud storage.
#
#
#
#
#

from discord_webhook import DiscordWebhook #NEED TO INSTALL (run in command prompt: pip install discord-webhook)
import asyncio
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import os
import requests
import json
import urllib.request
import subprocess
import time

#variables
token = 'TOKEN_HERE'
channelId = 'CHANNEL_ID_TO_STORE_FILES_HERE'
limit = 100

wbhkurl = 'WEBHOOK_URL_HERE'
webhook = DiscordWebhook(url=wbhkurl, username="Cloud Storage Webhook") #Can change username if you want


master = 'master-record.txt'

parts = 0
chunk_size = 18 * 1024 * 1024  #18Mb; Discord limit = 20Mb, so I put 18 to be safe

urls = []
ffi = 0
g_progress = ''



#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def upload_file_dialog():
    try:
        file = filedialog.askopenfilename()
        filename = os.path.basename(file)
        finfo = os.stat(file)
        print('Selected file:', file)
    except FileNotFoundError:
        tk.messagebox.showerror(title='Error', message='Invalid file name or file doesn\'t exist.')
        return
    
    if checkifduplicate(filename, master):
        print('The filename is already present in the master record.')
    
    else:
        print('The filename is not present in the master record.')
        
        if finfo.st_size <= 18874368: #1024 * 1024 * 18
            upload_file(file, False, False)
        else:
            num_parts = split_file(file, chunk_size) #splits
            part_one = True
            #part_one is if the file being uploaded is the first part (part 1).
            #if it is, then the upload_file() function will add the filename to the master record, with the tag [SPLIT].
            #after that, part_one is set to False, so the filename is not added to the record everytime another part is uploaded
            for part_no in range(num_parts):
                num = part_no + 1
                file_parts = f'{file}.part{num}'
                upload_file(file_parts, True, part_one)
                part_one = False
                del num
            webhook = DiscordWebhook(url=wbhkurl, content='<PADDING>')
            response = webhook.execute()
    return

def upload_folder_dialog():
    foldername = filedialog.askdirectory()
    if foldername == '':
            tk.messagebox.showerror(title='Error', message='Invalid folder name or folder doesn\'t exist.')
            return
    print('Selected folder:', foldername)
    tarball_path = f'{foldername}.tar'

    tar_command = ['tar', '-cf', tarball_path, '-C', foldername, '.']
    subprocess.run(tar_command)

    compressed_tarball_path = f'{foldername}.tar.bz2'

    bzip2_command = ['bzip2', tarball_path, '-c', '>', compressed_tarball_path]
    subprocess.run(' '.join(bzip2_command), shell=True)

    #
    
    upload_file(compressed_tarball_path)
    os.remove(tarball_path)
    os.remove(compressed_tarball_path)
    
    return



def download_dialog():
    #global since its used in another function
    global g_filebrowse
    dwl = tk.Tk()
    dwl.title('Download a file/folder')
    dwl.config(bg='#1c1c1c')
    g_title = tk.Label(dwl, text='Download file', width=50, height=1, fg='#dedede', bg='#141414', font='fixedsys')
    g_title.pack()

    #for listbox
    lines = []
    with open(master, "r") as file:
        lines = file.readlines()

    g_filebrowse = tk.Listbox(dwl, height=20, width=50, selectmode='SINGLE', fg='#dedede', bg='#141414', font='fixedsys')
    index = 0
    for line in lines:
        index = index + 1
        if '.tar.bz2' in line:
            foldername = f'{line.strip()} <FOLDER>'
            g_filebrowse.insert(index, foldername)
            #if a file has the extension used for compression, mark it as [FOLDER] at the end.
        else:
            g_filebrowse.insert(index, line.strip())

    g_filebrowse.pack()

    g_dwl_file_sel = tk.Button(dwl, text='Download', command=dwl_file_sel, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')
    g_dwl_file_sel.pack()

    return

def delete_file_folder_dialog():
    global g_deletebrowse
    global delete

    delete = tk.Tk()
    delete.title('Delete a file/folder')

    delete.config(bg='#1c1c1c')
    
    g_title = tk.Label(delete, text='Download file', width=50, height=1, fg='#dedede', bg='#141414', font='fixedsys')
    g_title.pack()

    #listbox
    lines = []
    with open(master, "r") as file:
        lines = file.readlines()

    g_deletebrowse = tk.Listbox(delete, height=20, width=50, selectmode='SINGLE', fg='#dedede', bg='#141414', font='fixedsys')
    index = 0
    for line in lines:
        index = index + 1
        if '.tar.bz2' in line:
            foldername = f'{line.strip()} <FOLDER>'
            g_deletebrowse.insert(index, foldername)
        else:
            g_deletebrowse.insert(index, line.strip())

    g_deletebrowse.pack()

    g_del_file_sel = tk.Button(delete, text='Delete', command=del_file_sel, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')
    g_del_file_sel.pack()
    

def checkifduplicate(filename, file_path):
    with open(file_path, "r") as file:
        for line in file:
            if line.strip() == filename:
                return True
    return False



#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#get selected FILE or FOLDER (STORED AS A FILE) to pass to the find function
def dwl_file_sel():
    for i in g_filebrowse.curselection():
        print(g_filebrowse.get(i))
        dwl_file_sel = g_filebrowse.get(i)
        if '<SPLIT>' in dwl_file_sel:
            
            print('unf')
            
            dwl_file_sel = dwl_file_sel.replace(' <SPLIT>', '')
            find_split(dwl_file_sel)
            print(urls)
            for each_url in urls:
                download_file(each_url)
            num_parts = ffi - 1
            join_files(dwl_file_sel, num_parts)
            print('Downloaded and joined')
            
        elif '<FOLDER>' in dwl_file_sel:
            
            dwl_file_sel = dwl_file_sel.replace(' <FOLDER>', '')
            url = find(dwl_file_sel)
            download_file(url)
            
        else:
            
            url = find(dwl_file_sel)
            download_file(url)
            
    return



def upload_file(file, multiple, p_one):
    try:
        filename = os.path.basename(file)
        print(f'Uploading "{file}"')
        with open(file, 'rb') as f:
            webhook = DiscordWebhook(url=wbhkurl, content=filename)
            webhook.add_file(file=f.read(), filename=filename)
            response = webhook.execute()
            print(response)
            print('Successfully uploaded')
            #add to MASTER RECORD (which is a txt file located in the same directory as the script)
            if multiple == True:
                if p_one == True:
                    with open(master, 'a') as m:
                        filename = filename.replace('.part1', '') #assume its .part1, since its the first iteration (hence "if p_one == True:")
                        filename = filename.replace(' ', '_') #discord changes spaces to underscores _
                        m.write(filename + ' <SPLIT>\n')
                else:
                    print('Skip writing to master record')
                    #do nothing section. this is because it is uploading a part of a file which isnt the first, which means its already in the master record.
            else:
                with open(master, 'a') as m:
                    filename = filename.replace(' ', '_') #discord changes spaces to underscores _
                    m.write(filename + '\n')
            return
        return

        
    except:
        print(f'There was an error uploading "{file}" to the cloud. Please check your connection and try again.')
    return


def download_file(url):
    headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    urlfilename = os.path.basename(url)
    print(urlfilename)
    with open(urlfilename, 'wb') as f:
        f.write(response.content)
    strippedname = urlfilename.replace('.tar.bz2', '')
    if '.tar.bz2' in urlfilename:
        
        os.mkdir(strippedname)
        tarball_path = urlfilename

        tar_command = ['tar', '-xvjf', tarball_path, '-C', strippedname]
        subprocess.run(tar_command)
        os.remove(tarball_path)
    elif '.part' in urlfilename:
        print('not opening PART file')
    else:
        os.system(urlfilename)
    print('File downloaded and opened')
    return



#finds the attachment URL to pass to the download_file function
def find(filename):
    global last_id #idk but y not i guess
    file_found = False #file not found yet
    ffi = 0 #set File Finder Index to 1. This is because the first search of 100 messages requires a slightly shorter GET request.
    #If the while loop runs when ffi = 1, it will run the shorter GET request. If it is >1, it will run a slightly different longer GET request.

    #headers
    headers = {'Authorization':'Bot ' + token}

    #getting most recent 100 messages. log the ID last message of the set of 100, in case the file is not found. Then do another search with ?before=100th_msg_ID
    while file_found == False:
        ffi = ffi + 1
        if ffi == 1:
            #shorter GET url (no ?before={last_id})
            r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?limit={limit}', headers=headers)
            
            response = json.loads(r.text)
            #get the last msg ID of the 100 msgs
            n = limit - 1
            last_id = response[n]['id']

            for msg in response:
                try:
                    url = msg['attachments'][0]['url']
                    print(url)
                    if filename in url:
                        print('File url found')
                        file_found = True
                        print('Downloading')
                        print('Complete')
                        break
                    else:
                        print('File not found')
                except IndexError:
                    print('Message has no attachment...(or an error has occured)')
        elif ffi > 1:
            #longer GET
            
            r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?before={last_id}&limit={limit}', headers=headers)
            
            response = json.loads(r.text)
            n = limit - 1
            last_id = response[n]['id']

            for msg in response:
                try:
                    url = msg['attachments'][0]['url']
                    print(url)
                    print(msg['id'])
                    if filename in url:
                        print('File url found')
                        file_found = True
                        print('Downloading')
                        print('Complete')
                        break
                    else:
                        print('File not found')
                except IndexError:
                    print('No attachment/Other error')

    return url


def find_split(filename):
    global urls #the URL array
    global ffi
    urls = []
    file_found = False #file not found yet
    ffi = 0 
    #headers
    headers = {'Authorization':'Bot ' + token}

    #getting most recent 100 messages. log the ID last message of the set of 100, in case the file is not found. Then do another search with ?before=100th_msg_ID
    while file_found == False:
        ffi = ffi + 1
        if ffi == 1:
            #shorter GET url (no ?after={first_id})
            r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?limit={limit}', headers=headers)
            
            response = json.loads(r.text)
            #get the msg ID. IDK why i called it first_id
            n = 1
            first_id = response[n]['id']
            
            #modify the filename to get filename.part1
            current_split_name = f'{filename}.part1'

            for msg in response:
                try:
                    url = msg['attachments'][0]['url']
                    print(url)
                    if current_split_name in url:
                        print('Part1 Found')
                        urls.append(url)
                        first_id = response[n]['id']
                        break
                    
                    else:
                        print('File not found')
                    n += 1
                except IndexError:
                    print('Message has no attachment...(or an error has occured)')
        elif ffi > 1:
            #longer GET
            
            r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?after={first_id}&limit=1', headers=headers)
            
            response = json.loads(r.text)            

            #modify the filename to get filename.part(n)
            current_split_name = f'{filename}.part{ffi}'

            #if id in response:
            for msg in response:
                try:
                    url = msg['attachments'][0]['url']
                    print(url)
                    print(msg['id'])
                    if current_split_name in url:
                        print(f'Part{ffi} Found')
                        urls.append(url)
                        first_id = msg['id']
                        break
                    else:
                        print('File not found')
                        file_found = True
                except IndexError:
                    print('No attachment/Other error')
                    file_found = True
            
    return urls

def split_file(filename, chunk_size):
    with open(filename, 'rb') as f:
        part_num = 0
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            part_num += 1
            part_filename = f'{filename}.part{part_num}'
            with open(part_filename, 'wb') as part_file:
                part_file.write(chunk)

    return part_num


def join_files(filename, num_parts):
    with open(filename, 'wb') as f:
        for part_num in range(1, num_parts + 1):
            part_filename = f'{filename}.part{part_num}'
            with open(part_filename, 'rb') as part_file:
                f.write(part_file.read())
            #Remove the part file after joining
            os.remove(part_filename)

def del_file_sel():
    for i in g_deletebrowse.curselection():
        print(g_deletebrowse.get(i))
        linetext = g_deletebrowse.get(i)

    try:
        print(linetext)
    except:
        tk.messagebox.showerror(title='Error', message='No file/folder selected.')
        return
    with open(master, 'r') as file:
        lines = file.readlines()

    with open(master, 'w') as file:
        for line in lines:
            if line.strip() == linetext and line.rstrip("\n") == linetext:
                continue  
            file.write(line)
    delete.destroy()
    delete_file_folder_dialog()
        
#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

###GUI###
#this is the main screen with buttons etc.
def main():
    #global g_progress
    window = tk.Tk()
    window.title('Infinite Cloud Storage')
    window.geometry('380x150')
    window.config(bg='#1c1c1c')
    
    g_topframe = tk.Frame(window, bg='#1c1c1c')
    g_middleframe = tk.Frame(window, bg='#1c1c1c', pady=15)
    g_bottomframe = tk.Frame(window, bg='#1c1c1c', pady=2)
    
    g_title = tk.Label(g_topframe, text='Infinite Cloud Storage via Discord', fg='#dedede', bg='#141414', width=60, height=3, font='fixedsys')

    g_upl_fil_btn = tk.Button(g_middleframe, text='Upload File', command=upload_file_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_upl_fol_btn = tk.Button(g_bottomframe, text='Upload Folder', command=upload_folder_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_dwl_fil_fol_btn = tk.Button(g_middleframe, text='Download File/Folder', command=download_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_del_fil_fol_btn = tk.Button(g_bottomframe, text='Delete File', command=delete_file_folder_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')


    #packing
    g_title.pack()
    g_upl_fil_btn.pack(side='left')
    g_upl_fol_btn.pack(side='left')
    g_dwl_fil_fol_btn.pack(side='right')
    g_del_fil_fol_btn.pack(side='right')
    g_topframe.pack()
    g_middleframe.pack()
    g_bottomframe.pack()

    try:
        icon = tk.PhotoImage(file = 'main.png')
        window.iconphoto(False, icon)
    except:
        print('Icons not available')


        
    window.mainloop()




#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

main()
        
