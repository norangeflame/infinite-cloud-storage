### Unlimited Cloud Storage via Discord ###
#------------------------------------------
# Usage:
# - Run the application, and press the "config" button. Enter in your bot token, webhook url, and the channelID to send messages in. Entering incorrect/expired values will break the cloud storage, and any attempt to upload/download files will result in errors. 
# - NOTE: please make sure you don't use the file storing channel for general messages. This will cause longer download times.
# - NOTE: please make sure the Webhook is set to send messages to the file storing channel. A mismatch in your channelID and the channel
#         that the webhook is set to will break the cloud storage.
# 
# All coding by norangeflame

from discord_webhook import DiscordWebhook #NEED TO INSTALL (run in command prompt: pip install discord-webhook)
import tkinter as tk
from tkinter import filedialog
import os
import requests
import json
import subprocess
import time
import configparser

#variables
r_config = configparser.ConfigParser()
r_config.sections()
r_config.read('config.ini')
token = r_config['DEFAULT' ]['token']
wbhkurl = r_config['DEFAULT' ]['webhook_url']
channelId = r_config['DEFAULT' ]['channelId']

webhook = DiscordWebhook(url=wbhkurl, username="Cloud Storage Webhook")


master = 'master-record.txt'
limit = 100
parts = 0
chunk_size = 24 * 1024 * 1024  #25Mb; Discord limit = 25Mb, so I put 24 to be safe
urls = []
ffi = 0
g_progress = ''
g_dwl_status = ''
g_status = ''
cs = 10 * 1024 * 1024  #10Mb
units_size = 1024 * 1024 #1Mb
units = 'Mb/s'
config_token = ''
config_wbhkurl = ''
config_channelId = ''

#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


def update_main_status(labeltext):
    global g_status
    g_status.config(text=labeltext)
    g_status.update_idletasks() 

def upload_file_dialog():
    update_main_status('Choosing file...')
    try:
        file = filedialog.askopenfilename()
        filename = os.path.basename(file)
        finfo = os.stat(file)
        print('Selected file:', file)
    except FileNotFoundError:
        tk.messagebox.showerror(title='Error', message='Invalid file name or file doesn\'t exist.')
        update_main_status('Ready')
        return
    update_main_status('Uploading...')
    if checkifduplicate(filename, master):
        print('The filename is already present in the master record.')
        tk.messagebox.showerror(title='Error', message='This file has already been uploaded.')
    
    else:
        print('The filename is not present in the master record.')
        
        if finfo.st_size <= chunk_size: #1024 * 1024 * 18
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
        
    labeltext = 'Ready'
    update_main_status('Ready')
    return

def upload_folder_dialog():
    update_main_status('Choosing folder...')
    foldername = filedialog.askdirectory()
    if foldername == '':
            tk.messagebox.showerror(title='Error', message='Invalid folder name or folder doesn\'t exist.')
            update_main_status('Ready')
            return
    print('Selected folder:', foldername)
    tarball_path = f'{foldername}.tar'
    update_main_status('Compressing folder...')
    tar_command = ['tar', '-cf', tarball_path, '-C', foldername, '.']
    subprocess.run(tar_command)

    compressed_tarball_path = f'{foldername}.tar.bz2'

    bzip2_command = ['bzip2', tarball_path, '-c', '>', compressed_tarball_path]
    subprocess.run(' '.join(bzip2_command), shell=True)

    #
    update_main_status('Uploading folder...')
    upload_file(compressed_tarball_path, False, False)
    update_main_status('Ready')
    os.remove(tarball_path)
    os.remove(compressed_tarball_path)

    return



def download_dialog():
    #global since its used in another function
    global g_filebrowse
    global g_dwl_status
    
    dwl = tk.Tk()
    dwl.title('Download a file/folder')
    dwl.config(bg='#1c1c1c')
    dwl.resizable(False, False)
    g_frame = tk.Frame(dwl, bg='#1c1c1c')
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
    
    g_dwl_status = tk.Label(g_frame, text='Ready', width=50, height=1, fg='#dedede', bg='#141414', font='fixedsys')
    
    
    g_dwl_file_sel = tk.Button(g_frame, text='Download', command=dwl_file_sel, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')
    g_dwl_file_sel.pack()
    g_dwl_status.pack()
    g_frame.pack()

    return

def delete_file_folder_dialog():
    global g_deletebrowse
    global delete

    delete = tk.Tk()
    delete.title('Delete a file/folder')

    delete.config(bg='#1c1c1c')
    delete.resizable(False, False)
    g_title = tk.Label(delete, text='Delete file', width=50, height=1, fg='#dedede', bg='#141414', font='fixedsys')
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


def update_dwl_status(text):
    g_dwl_status.config(text=text)
    g_dwl_status.update_idletasks()
 

#get selected FILE or FOLDER (STORED AS A FILE) to pass to the find function
def dwl_file_sel():
    update_dwl_status('Downloading...')
    update_main_status('Downloading...')
    for i in g_filebrowse.curselection():
        print(g_filebrowse.get(i))
        dwl_file_sel = g_filebrowse.get(i)
        if '<SPLIT>' in dwl_file_sel:
                        
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
    update_dwl_status('Ready')
    update_main_status('Ready')
    return



def upload_file(file, multiple, p_one):
    try:
        filename = os.path.basename(file)
        filename = filename.replace(' ', '_') #discord changes spaces to underscores _
        filename = filename.replace('!', '') #discord strips most special characters
        filename = filename.replace('@', '') #discord strips most special characters
        filename = filename.replace('#', '') #discord strips most special characters
        filename = filename.replace('$', '') #discord strips most special characters
        filename = filename.replace('%', '') #discord strips most special characters
        filename = filename.replace('^', '') #discord strips most special characters
        filename = filename.replace('&', '') #discord strips most special characters
        filename = filename.replace('*', '') #discord strips most special characters
        filename = filename.replace('(', '') #discord strips most special characters
        filename = filename.replace(')', '') #discord strips most special characters
        filename = filename.replace('=', '') #discord strips most special characters
        filename = filename.replace('+', '') #discord strips most special characters
        filename = filename.replace('[', '') #discord strips most special characters
        filename = filename.replace(']', '') #discord strips most special characters
        filename = filename.replace('{', '') #discord strips most special characters
        filename = filename.replace('}', '') #discord strips most special characters
        filename = filename.replace(';', '') #discord strips most special characters
        filename = filename.replace(',', '') #discord strips most special characters

        
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
                        m.write(filename + ' <SPLIT>\n')
                else:
                    print('Skip writing to master record')
                    #do nothing section. this is because it is uploading a part of a file which isnt the first, which means its already in the master record.
            else:
                with open(master, 'a') as m:
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
    response = requests.get(url, headers=headers, stream=True)
    urlfilename = os.path.basename(url)
    print(urlfilename)

    total_size = int(response.headers.get('content-length', 0))
    downloaded_size = 0
    start_time = time.time()
    
    with open(urlfilename, 'wb') as f:
        for chunk in response.iter_content(chunk_size=cs):
            if chunk:
                f.write(chunk)
                downloaded_size = downloaded_size + len(chunk)
                elapsed_time = time.time() - start_time
                speed = downloaded_size / elapsed_time
                speed = speed / units_size
                speed = round(speed)
                mb_size = downloaded_size / units_size
                mb_tot_size = total_size / units_size
                mb_size = round(mb_size, 2)
                mb_tot_size = round(mb_tot_size, 2)
                print(f'{speed} {units} - {mb_size}/{mb_tot_size}MB')
                update_main_status(f'{speed}{units} ({mb_size}/{mb_tot_size}MB)')
                update_dwl_status(f'{speed}{units} ({mb_size}/{mb_tot_size}MB)')



    
    strippedname = urlfilename.replace('.tar.bz2', '')
    if '.tar.bz2' in urlfilename:
        print('Decompressing folder')
        os.makedirs(strippedname, exist_ok=True)
        tarball_path = urlfilename

        tar_command = ['tar', '-xvjf', tarball_path, '-C', strippedname]
        subprocess.run(tar_command)
        os.remove(tarball_path)
        update_main_status('Ready')
        update_dwl_status('Ready')
    elif '.part' in urlfilename:
        print('Downloaded; not opening PART file')
        update_main_status('Combining files...')
        update_dwl_status('Combining files...')
    else:
        #os.system(urlfilename)
        print('File downloaded')
        update_main_status('Ready')
        update_dwl_status('Ready')
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


    
    r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?limit=1', headers=headers)    
    response = json.loads(r.text)
    n = 1
    last_id = response[0]['id']
    print('First')       
    #getting most recent 100 messages. log the ID last message of the set of 100, in case the file is not found. Then do another search with ?before=100th_msg_ID
    while file_found == False:
        ffi = ffi + 1
        if ffi == 1:
            first_file_found = False
            while first_file_found == False:
                time.sleep(1)
                #shorter GET ur l (no ?after={first_id})
                r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?limit={limit}&before={last_id}', headers=headers)
                #print(response)
                response = json.loads(r.text)
                #get the msg ID. IDK why i called it first_id
                n = limit - 1
                e = 1
                try:
                    first_id = response[e]['id']
                    last_id = response[n]['id']
                    #print(f'{first_id}; search function')
                except:
                    print('Error')
                #modify the filename to get filename.part1
                current_split_name = f'{filename}.part1'

                for msg in response:
                    try:
                        if len(msg['attachments']) > 0:
                            url = msg['attachments'][0]['url']
                            print(url)
                            if current_split_name in url:
                                print('Part1 Found')
                                urls.append(url)
                                first_id = response[e]['id']
                                first_file_found = True
                                break
                            
                            else:
                                print('File not found')
                        else:
                            print('Message has no attachment')
                    #n += 1
                    except:
                        print('an error has occured')
        elif ffi > 1:
            #longer GET
            
            r = requests.get(f'https://discord.com/api/v9/channels/{channelId}/messages?after={first_id}&limit=1', headers=headers)
            
            response = json.loads(r.text)            

            #modify the filename to get filename.part(n)
            current_split_name = f'{filename}.part{ffi}'
            print('get all func')
            print(ffi)
            #if id in response:
            for msg in response:
                try:
                    if len(msg['attachments']) > 0:
                        url = msg['attachments'][0]['url']
                        print(url)
                        print(msg['id'])
                        if current_split_name in url:
                            print(f'Part{ffi} Found')
                            urls.append(url)
                            first_id = msg['id']
                            break
                        else:
                            print('File not found; last PART file reached')
                            file_found = True
                    else:
                        print('No attachment; last PART file reached')
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
    update_main_status('Ready')
    update_dwl_status('Ready')
    return

def del_file_sel():
    for i in g_deletebrowse.curselection():
        print(g_deletebrowse.get(i))
        linetext = g_deletebrowse.get(i)

    try:
        print(linetext)
    except:
        tk.messagebox.showerror(title='Error', message='No file/folder selected.')
        return

    if '.tar.bz2' in linetext:
        linetext = linetext.replace(' <FOLDER>', '')
    with open(master, 'r') as file:
        lines = file.readlines()

    with open(master, 'w') as file:
        for line in lines:
            if line.strip() == linetext and line.rstrip("\n") == linetext:
                continue  
            file.write(line)
    delete.destroy()
    delete_file_folder_dialog()

def update_config(t, w, i):
    global token
    global wbhkurl
    global channelId

    #msg
    tk.messagebox.showinfo(title='Saved', message='Information saved. You will not need to re-enter it in the future, unless you wish to modify.')

    #set in case not restarted
    token = t.strip()
    wbhkurl = w.strip()
    channelId = i.strip()

    #writing
    w_config = configparser.ConfigParser()
    w_config['DEFAULT']['token'] = token
    w_config['DEFAULT']['webhook_url'] = wbhkurl
    w_config['DEFAULT']['channelId'] = channelId
    with open('config.ini', 'w') as configfile:
        w_config.write(configfile)
    return


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#CONFIG GUI
def config():
    config_token = tk.StringVar()
    config_wbhkurl = tk.StringVar()
    config_channelId = tk.StringVar()

    def call_config_update():
            update_config(g_config_token_entry.get(), g_config_webhook_entry.get(), g_config_channelid_entry.get())
            config_window.destroy()

    #window config
    config_window = tk.Tk()
    config_window.title('Config Menu')
    config_window.geometry('500x220')
    config_window.config(bg='#1c1c1c')
    config_window.resizable(False, False)
    
    try:
        icon = tk.PhotoImage(file = 'main.png')
        config_window.iconphoto(False, icon)
    except:
        print('Icons not available')

    #framing
    configframetoken = tk.Frame(config_window, bg='#1c1c1c', pady=10)
    configframeurl = tk.Frame(config_window, bg='#1c1c1c', pady=10)
    configframechid = tk.Frame(config_window, bg='#1c1c1c', pady=10)
    #main
    g_config_token_label = tk.Label(configframetoken, text='Discord bot token:', fg='#dedede', bg='#1c1c1c', font='fixedsys', justify='left')
    g_config_webhookurl_label = tk.Label(configframeurl, text='Discord webhook URL', fg='#dedede', bg='#1c1c1c', font='fixedsys')
    g_config_channelid_label = tk.Label(configframechid, text='Discord ChannelID', fg='#dedede', bg='#1c1c1c', font='fixedsys')
    g_config_token_entry = tk.Entry(configframetoken, textvariable=config_token, bg='#141414', fg='#dedede', width=60, exportselection=0, font='fixedsys', insertbackground='white')
    g_config_webhook_entry = tk.Entry(configframeurl, textvariable=config_wbhkurl, bg='#141414', fg='#dedede', width=60, exportselection=0, font='fixedsys', insertbackground='white')
    g_config_channelid_entry = tk.Entry(configframechid, textvariable=config_channelId, bg='#141414', fg='#dedede', width=60, exportselection=0, font='fixedsys', insertbackground='white')
    g_config_ok_btn = tk.Button(config_window, text='OK', command=call_config_update, width=10, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')
    #packing
    g_config_token_label.pack()
    g_config_webhookurl_label.pack()
    g_config_channelid_label.pack()
    g_config_token_entry.pack()
    g_config_webhook_entry.pack()
    g_config_channelid_entry.pack()

    configframetoken.pack()
    configframeurl.pack()
    configframechid.pack()

    g_config_ok_btn.pack()
    return



    
###GUI###
#this is the main screen with buttons etc.
def main():
    #global g_progress
    #window config
    global config_token
    global config_wbhkurl
    global config_channelId
    global g_status
    window = tk.Tk()
    window.title('Infinite Cloud Storage')
    window.geometry('380x160')
    window.config(bg='#1c1c1c')
    window.resizable(False, False)
    
    #framing
    g_topframe = tk.Frame(window, bg='#1c1c1c')
    g_middleframe = tk.Frame(window, bg='#1c1c1c', pady=15)
    g_bottomframe = tk.Frame(window, bg='#1c1c1c', pady=2)
    g_statusframe = tk.Frame(window, bg='#141414')
    
    #main
    g_title = tk.Label(g_topframe, text='Infinite Cloud Storage via Discord', fg='#dedede', bg='#141414', width=60, height=3, font='fixedsys')

    g_upl_fil_btn = tk.Button(g_middleframe, text='Upload File', command=upload_file_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_upl_fol_btn = tk.Button(g_bottomframe, text='Upload Folder', command=upload_folder_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_dwl_fil_fol_btn = tk.Button(g_middleframe, text='Download File/Folder', command=download_dialog, width=20, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_del_fil_fol_btn = tk.Button(g_bottomframe, text='Delete File', command=delete_file_folder_dialog, width=20, height=1, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_config_btn = tk.Button(g_statusframe, text='Config', command=config, width=8, fg='#dedede', bg='#141414', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')

    g_status = tk.Label(g_statusframe, text='Ready', width=380, height=1, fg='#dedede', bg='#141414', font='fixedsys', anchor='w')

    #packing
    g_title.pack()
    g_upl_fil_btn.pack(side='left')
    g_upl_fol_btn.pack(side='left')
    g_dwl_fil_fol_btn.pack(side='right')
    g_del_fil_fol_btn.pack(side='right')
    g_config_btn.pack(side='right')
    g_status.pack(side='left')
    g_topframe.pack()
    g_middleframe.pack()
    g_bottomframe.pack()
    g_statusframe.pack()

    try:
        icon = tk.PhotoImage(file = 'main.png')
        window.iconphoto(False, icon)
    except:
        print('Icons not available')


    #config variables  







    window.mainloop()




#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

main()
        
