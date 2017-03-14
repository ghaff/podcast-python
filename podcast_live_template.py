####################
# Podcast post-production
#!/usr/bin/python

# Gordon Haff
#
# Requires:
# boto   https://github.com/boto/boto.git
# mpeg1audio   https://github.com/Ciantic/mpeg1audio/
# pydub (which requires ffmpeg to be installed) https://github.com/jiaaro/pydub
# Edited MP3 file
# MP3 intro and outro segments
# Image file public on S3
# header XML in header txt file
# text file to store individual podcast XML, even if initially (mostly) empty. 
#       Needs lines:
#       </channel>
#       </rss>
# An existing RSS podcast feed XML file (or a null file)
# Existing AWS S3 bucket and credentials
# Supporting files in same directory as MP3 file
#
# set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables
# Redefine the global filename variables for your needs
# Redefine the bucket name for your needs
# 
# This script:
# 1. Gets information such as duration from MP3 file
# 2. Allows user to input additional information (title, etc.)
# 3. Updates iTunes XML podcast file
# 4. Concatenates MP3 file with intro and outro segments
# 5. Creates OGG file version
# 6. Uploads XML and MP3 and OGG files to Amazon S3 and makes PUBLIC
#

from Tkinter import *
from pydub import AudioSegment 
import tkFileDialog
import os
import boto 
from boto.s3.key import Key
from os import path
import time
import mpeg1audio  
from gdata import service
import gdata
import atom
import shutil

#####################################################
# Define this stuff
# set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY as environment variables
bucket_name='MYPODCASTBUCKET'
##############################################

def open_file_dialog():

    global filename
    global oggexists
    global Filelength
    global FilelengthStr
    global DurationStr
    global OggFilename
    global iTunesFile
    global iTunesHeader
    global iTunesItems
    global theDirname

    # Change names as desired
    leadIn = "podcastintro.mp3"       #intro to prepend
    leadOut = "podcastoutro.mp3"         #outro to append
    iTunesFile = "itunesrss.xml"         #your podcast feed
    iTunesHeader = "itunesheader.txt"    #the header on your podcast feed file
    iTunesItems = "itunesitems.txt"      #you'll need to populate with XML for a podcast

    filename = tkFileDialog.askopenfilename(filetypes=[("MP3 files",".mp3")])
    v.set(filename)
    
    FileBase, FileExtension = path.splitext(filename)
    theDirname = path.dirname(filename)
    
    renameOriginal = FileBase + "_original" + FileExtension
    shutil.copy2(filename,renameOriginal)
    
    # add path to the various locations
    leadIn = path.join(theDirname,leadIn)
    leadOut = path.join(theDirname,leadOut)
    iTunesFile = path.join(theDirname,iTunesFile)
    iTunesHeader = path.join(theDirname,iTunesHeader)
    iTunesItems = path.join(theDirname,iTunesItems)
    
    # Concatenate MP3 file with header and footer
    baseSegment = AudioSegment.from_mp3(filename)
    introSegment = AudioSegment.from_mp3(leadIn)
    outroSegment = AudioSegment.from_mp3(leadOut)

    completeSegment = introSegment + baseSegment + outroSegment

    #export new MP3 file and also an ogg version
    completeSegment.export(filename,"mp3")
    OggFilename = FileBase + '.ogg'
    completeSegment.export(OggFilename,"ogg")

    # Error checking from prior version. "Shouldn't" be possible to happen now
    oggexists = True
    if not path.isfile(OggFilename):
        oggexists = False
        StatusText.set("Status: OGG file missing")

    Filelength = path.getsize(filename)
    FilelengthStr.set("Filelength (bytes): " + str(Filelength))

    timestruc = time.gmtime(path.getmtime(filename))

    TimestampEntry.delete(0,END)
    TimestampEntry.insert(0,time.strftime("%a, %d %b %G %T",timestruc) + " GMT")

    mp3 = mpeg1audio.MPEGAudio(filename)
    DurationStr = str(mp3.duration)
    DurationLabelStr.set("Duration: " + DurationStr)

def do_stuff():

    createXML()
    uploadtoAMZN()
    StatusText.set("Status: Success (AFAIK)")

def createXML():

    global MP3url

    # create an XML file containing contents for new </item> for iTunes
    FileBase, FileExtension = path.splitext(filename)
    XMLfilename = FileBase + '.xml'
    MP3url = "http://s3.amazonaws.com/"+bucket_name+"/"+path.basename(filename)
    inp = file(XMLfilename, 'w')

    inp.write("<item>\n")
    inp.write("<title>"+PodcastTitleEntry.get()+"</title>\n")
    inp.write("<itunes:subtitle>"+PodcastSubtitleEntry.get()+"</itunes:subtitle>\n")
    inp.write("<itunes:summary>"+PodcastSummaryText.get(1.0,END)+"</itunes:summary>\n")
    inp.write("<enclosure url=\""+MP3url+"\" length=\""+str(Filelength)+"\" type=\"audio/mpeg\" />\n")
    inp.write("<guid>"+MP3url+"</guid>\n")
    inp.write("<pubDate>"+TimestampEntry.get()+"</pubDate>\n")
    inp.write("<itunes:duration>"+DurationStr+"</itunes:duration>\n")
    inp.write("<itunes:keywords>cloud</itunes:keywords>\n")
    inp.write("<itunes:explicit>no</itunes:explicit>\n")
    inp.write("</item>")
    inp.write("")

    inp.close()

    #Now concatenate to make a new itunesxml.xml file
    
    #create backup of existing iTunes XML file in case something goes kaka
    iTunesBackup = path.join(theDirname,"itunesxmlbackup.xml")
    shutil.copy2(iTunesFile,iTunesBackup)

    #create temporary iTunes item list (to overwrite the old one later on)    
    outfile = file("iTunestemp.xml", 'w')
    
    # create a new items file
    with open(XMLfilename) as f:
        for line in f:
            outfile.write(line)
    with open(iTunesItems) as f:
        for line in f:
            outfile.write(line) 
    outfile.close()
        
    #replace the old items file with the new one
    shutil.copy2("iTunestemp.xml",iTunesItems)
    
    #now we're ready to create the new iTunes File  
    outfile = file(iTunesFile, 'w')
    
    # create a new items file
    with open(iTunesHeader) as f:
        for line in f:
            outfile.write(line)
    with open(iTunesItems) as f:
        for line in f:
            outfile.write(line) 
    outfile.close()        

def uploadtoAMZN():

    # Upload files to Amazon S3
    # Change 'public-read' to 'private' if you want to manually set ACLs
    conn = boto.connect_s3()
    bucket = conn.get_bucket(bucket_name)
    k = Key(bucket)
    k.key = path.basename(filename)
    k.set_contents_from_filename(filename)
    k.set_canned_acl('public-read')

    if oggexists:
        k.key = path.basename(OggFilename)
        k.set_contents_from_filename(OggFilename)
        k.set_canned_acl('public-read')

    k.key = path.basename(iTunesFile)
    k.set_contents_from_filename(iTunesFile)
    k.set_canned_acl('public-read')

#####################################################

root = Tk()

Label(root,text="Podcast Title:").grid(row=1, sticky=W)

PodcastTitleEntry = Entry(root, width=80, borderwidth=1)
PodcastTitleEntry.grid(row=2, sticky=W)

Label(root,text="iTunes subtitle:").grid(row=3, sticky=W)

PodcastSubtitleEntry=Entry(root, width=80, borderwidth=1)
PodcastSubtitleEntry.grid(row=4, sticky=W)

Label(root,text="iTunes summary:").grid(row=5, sticky=W)

PodcastSummaryText=Text(root,width=80,height=4,borderwidth=2)
PodcastSummaryText.grid(row=6,sticky=W)


Button(root, text='Select file...',command=open_file_dialog).grid(row=9, column=0, sticky=W)

v = StringVar()
Label(root, textvariable=v,justify=LEFT,fg="blue").grid(row=10,sticky=W)

TimestampEntry = Entry(root,width=50,borderwidth=1)
TimestampEntry.grid(row=11,sticky=W)
TimestampEntry.insert(END,"Time/date (default filled in automatically from file)")

FilelengthStr = StringVar()
FilelengthStr.set("Filelength (bytes):")

FilelengthLabel = Label(root,textvariable=FilelengthStr)
FilelengthLabel.grid(row=12,sticky=W)

DurationLabelStr = StringVar()
DurationLabelStr.set("Duration: ");
DurationLabel = Label(root,textvariable=DurationLabelStr)
DurationLabel.grid(row=13,sticky=W)

Button(root, text='Go!',command=do_stuff).grid(row=14, sticky=W)

StatusText = StringVar()
StatusText.set("Status: Nothing to report")

StatusLabel=Label(root,textvariable=StatusText)
StatusLabel.grid(row=15, sticky=W)

root.mainloop()



