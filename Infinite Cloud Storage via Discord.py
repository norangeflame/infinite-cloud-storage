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
import re

#variables
r_config = configparser.ConfigParser()
r_config.sections()
r_config.read('config.ini')
#token = r_config['DEFAULT' ]['token']
wbhkurl = r_config['DEFAULT' ]['webhook_url']
#channelId = r_config['DEFAULT' ]['channelId']

webhook = DiscordWebhook(url=wbhkurl, username="Cloud Storage Webhook")


master = 'master-record.txt'
limit = 100
parts = 0
chunk_size = 24 * 1024 * 1024  #24Mb; Discord limit = 25Mb, so I put 24 to be safe
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


if not os.path.exists(master):
    f = open(master, "a")
    f.write('')
    f.close()


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
            upload_file(file)
            
        else:
            num_parts = split_file(file, chunk_size) #splits
            part_one = True
            #part_one is if the file being uploaded is the first part (part 1).
            #if it is, then the upload_file() function will add the filename to the master record, with the tag [SPLIT].
            #after that, part_one is set to False, so the filename is not added to the record everytime another part is uploaded
            for part_no in range(num_parts):
                num = part_no + 1
                file_parts = f'{file}.part{num}'
                upload_file(file_parts)
                part_one = False
                del num
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

    finfo = os.stat(compressed_tarball_path)
    update_main_status('Uploading folder...')
    if finfo.st_size <= chunk_size: #1024 * 1024 * 18
            upload_file(compressed_tarball_path)
            
    else:
        num_parts = split_file(compressed_tarball_path, chunk_size) #splits
        #part_one is if the file being uploaded is the first part (part 1).
        #if it is, then the upload_file() function will add the filename to the master record, with the tag [SPLIT].
        #after that, part_one is set to False, so the filename is not added to the record everytime another part is uploaded
        for part_no in range(num_parts):
            num = part_no + 1
            file_parts = f'{compressed_tarball_path}.part{num}'
            upload_file(file_parts)
            del num
    #upload_file(compressed_tarball_path, False, False)
    update_main_status('Ready')
    tk.messagebox.showinfo(title='Message', message='Folders are compressed before uploading, and will have a ".tar.bz2" file extension. They are automatically decompressed when downloaded.')
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

    #NOTES:
    #Only add the .part1 to this list (so you dont have repeats of all the parts). Strip the ".part1" when displayed, and when downloading add the ".part1" back
    g_filebrowse = tk.Listbox(dwl, height=20, width=50, selectmode='SINGLE', fg='#dedede', bg='#141414', font='fixedsys')
    index = 0
    for line in lines:
        index = index + 1
        if '.tar.bz2' in line:
            if '.tar.bz2.part' in line:
                if '.tar.bz2.part1' in line: #.tar.bz2.part1
                    foldername = line
                    foldername = foldername.replace('.part1', '')
                    foldername = os.path.basename(foldername.strip()) 
                    foldername = f'{foldername} <FOLDER>'
                    g_filebrowse.insert(index, foldername)
                else: #.tar.bz2.part'x'    
                    foldername = line
                    foldername = os.path.basename(foldername.strip()) 
            else: #.tar.bz2
                foldername = os.path.basename(line.strip()) 
                foldername = f'{foldername} <FOLDER>'
                g_filebrowse.insert(index, foldername)
        elif '.part1' in line:
            filename = line
            filename = filename.replace('.part1', '')
            filename = os.path.basename(filename.strip()) 
            g_filebrowse.insert(index, filename)
        elif not '.part' in line:
            filename = os.path.basename(line.strip()) 
            g_filebrowse.insert(index, filename)

            

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
            if '.tar.bz2.part' in line:
                if '.tar.bz2.part1' in line: #.tar.bz2.part1
                    foldername = line
                    foldername = foldername.replace('.part1', '')
                    foldername = os.path.basename(foldername.strip()) 
                    foldername = f'{foldername} <FOLDER>'
                    g_deletebrowse.insert(index, foldername)
                else: #.tar.bz2.part'x'    
                    foldername = line
                    foldername = os.path.basename(foldername.strip()) 
            else: #.tar.bz2
                foldername = os.path.basename(line.strip()) 
                foldername = f'{foldername} <FOLDER>'
                g_deletebrowse.insert(index, foldername)
            
        elif '.part1' in line:
            filename = line
            filename = filename.replace('.part1', '')
            filename = os.path.basename(filename.strip()) 
            g_deletebrowse.insert(index, filename)
        elif not '.part' in line:
            filename = os.path.basename(line.strip()) 
            g_deletebrowse.insert(index, filename)
            

            
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
        if '<FOLDER>' in dwl_file_sel:
            dwl_file_sel = dwl_file_sel.replace(' <FOLDER>', '')
        print(dwl_file_sel)
        find_split(dwl_file_sel)
        print(urls)
        for each_url in urls:
            download_file(each_url)
        num_parts = len(urls)
        if num_parts > 1:
            basename = dwl_file_sel
            join_files(basename, num_parts)

    update_dwl_status('Ready')
    update_main_status('Ready')
    return



def upload_file(file):
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

            print('Successfully uploaded')
            response = json.loads(response.text)
            print(response)
            url = response['attachments'][0]['url']
            print(url)
            with open(master, 'a') as m:
                m.write(f'{url}\n') #write the full URL to the master record, and start a new line

            #OLD FUNCTION:
            #add to MASTER RECORD (which is a txt file located in the same directory as the script)
            #if multiple == True:
                #if p_one == True:
                    #with open(master, 'a') as m:
                        #filename = filename.replace('.part1', '') #assume its .part1, since its the first iteration (hence "if p_one == True:")
                        #m.write(url + ' <SPLIT>\n') #write the URL to the master record, add the <SPLIT>
                        #m.write(f'{url}\n') #write the full URL to the master record, and start a new line
                #else:
                    #print('Skip writing to master record')
                    #do nothing section. this is because it is uploading a part of a file which isnt the first, which means its already in the master record.
            #else:
                #with open(master, 'a') as m:
                    #m.write(filename + '\n')
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
    if '.tar.bz2' in urlfilename and not '.tar.bz2.part' in urlfilename:
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
    else:
        #os.system(urlfilename)
        print('File downloaded')
        update_main_status('Ready')
        update_dwl_status('Ready')
    return



#finds the attachment URL to pass to the download_file function
def find_split(filename):
    global urls #the URL array
    global ffi
    urls = []
    file_found = False #file not found yet
    ffi = 0 
    lines = []
    with open(master, "r") as file:
        lines = file.readlines()

    index = 0
    for line in lines:
        index = index + 1
        var = os.path.basename(line.strip())
        var = re.sub(r'\.part\d+', '', var)
        print(var + '== ' + filename.strip() + '?')
        if filename.strip() == var:
            urls.append(line.strip())       
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
    update_main_status('Combining files...')
    update_dwl_status('Combining files...')
    with open(filename, 'wb') as f:
        for part_num in range(1, num_parts + 1):
            part_filename = f'{filename}.part{part_num}'
            with open(part_filename, 'rb') as part_file:
                f.write(part_file.read())
            #Remove the part file after joining
            os.remove(part_filename)
    strippedname = filename.replace('.tar.bz2', '')
    filename = os.path.basename(filename.strip()) 
    if '.tar.bz2' in filename:
        print('Decompressing folder')
        os.makedirs(strippedname, exist_ok=True)
        tarball_path = filename

        tar_command = ['tar', '-xvjf', tarball_path, '-C', strippedname]
        subprocess.run(tar_command)
        os.remove(tarball_path)
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
            if linetext in line.strip() and linetext in line.rstrip("\n"):
                continue  
            file.write(line)
    delete.destroy()
    delete_file_folder_dialog()

def update_config(w):
    global wbhkurl

    #msg
    tk.messagebox.showinfo(title='Saved', message='Information saved. You will not need to re-enter it in the future, unless you wish to modify.')

    #set in case not restarted
    wbhkurl = w.strip()

    #writing
    w_config = configparser.ConfigParser()
    w_config['DEFAULT']['webhook_url'] = wbhkurl
    with open('config.ini', 'w') as configfile:
        w_config.write(configfile)
    return


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#CONFIG GUI
def config():
    config_wbhkurl = tk.StringVar()

    def call_config_update():
            update_config(g_config_webhook_entry.get())
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
    configframeurl = tk.Frame(config_window, bg='#1c1c1c', pady=10)
    #main
    g_config_webhookurl_label = tk.Label(configframeurl, text='Discord webhook URL', fg='#dedede', bg='#1c1c1c', font='fixedsys')
    g_config_webhook_entry = tk.Entry(configframeurl, textvariable=config_wbhkurl, bg='#141414', fg='#dedede', width=60, exportselection=0, font='fixedsys', insertbackground='white')
    g_config_ok_btn = tk.Button(config_window, text='OK', command=call_config_update, width=10, fg='#dedede', bg='#262626', activebackground='#363636', activeforeground='#dedede', relief='flat', font='fixedsys')
    #packing
    g_config_webhookurl_label.pack()
    g_config_webhook_entry.pack()

    configframeurl.pack()

    g_config_ok_btn.pack()
    return



    
###GUI###
#this is the main screen with buttons etc.
def main():
    #global g_progress
    #window config
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


    window.mainloop()




#----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

main()
        
