#!/usr/bin/python3

from time import sleep
from datetime import datetime
from sh import gphoto2 as gp
import signal, os, subprocess, cups, glob
import RPi.GPIO as GPIO
import serial
import shutil

#flag 4 print
#printon = 0 # IF 1 THEN PRINT IF 0 THEN DONT PRINT

# full path to folder with old pictures
a_link_to_the_past="/home/pi/photobox/insta-vintage"
current_index_file=os.path.join(a_link_to_the_past, "current_index.json")

vorlagen_dir       = "/home/pi/photobox/vorlagen"
insta_vorlage_A = os.path.join(vorlagen_dir, "background_A.png")
insta_vorlage_B = os.path.join(vorlagen_dir, "background_B.png")
insta_vintage_vorlage_A = os.path.join(vorlagen_dir, "background_vintage_A.png")
insta_vintage_vorlage_B = os.path.join(vorlagen_dir, "background_vintage_B.png")
text_vorlage_A       = os.path.join(vorlagen_dir, "bg_text_A.png")
text_vorlage_B       = os.path.join(vorlagen_dir, "bg_text_B.png")
watermark_vorlage_A  = os.path.join(vorlagen_dir, "watermark_A.png")
watermark_vorlage_B  = os.path.join(vorlagen_dir, "watermark_B.png")
watermark_background_vorlage_A  = os.path.join(vorlagen_dir, "watermark_background_A.png")
watermark_background_vorlage_B  = os.path.join(vorlagen_dir, "watermark_background_B.png")
#vintagemode=False #True or False

# location of image vaults
save_location = "/home/pi/photobox/wand"
# vault for raw images
image_vault = "/home/pi/photobox/wand/saveimages"
# vault for modified images (watermarked, stitched, ...)
image_vault2 = "/home/pi/photobox/wand/savemerged"

def get_all_pictures(foldername, extension="*.jpg"):
    return glob.glob(os.path.join(foldername, extension))

def get_current_index(filename, number_of_files):
    if not os.path.exists(filename):
        # we have no previous index, let it start at 0
        with open(filename, "w") as f:
            f.write("0")
        return 0
    # read the last index from file, increment by one to get the current index
    with open(filename) as f:
        idx = int(next(f))
    idx = idx + 1
    # wrap-around for index, when at the last file, then start from beginning
    if idx >= number_of_files:
        idx = 0
    # write the updated index back to the file
    with open(filename, "w") as f:
        f.write("{:d}".format(idx))
    # return the index to use this round
    return idx

def get_vintagepic():
    all_images=get_all_pictures(a_link_to_the_past)
    img_idx = get_current_index(current_index_file, len(all_images))
    vintagename = all_images[img_idx]
    #print("list of all images: ", all_images)
    #print("the index of the image to use: ", img_idx)
    print("filename of the image to use: ", all_images[img_idx])
    return vintagename
    


#ls /dev/tty*
#ser = serial.Serial('/dev/ttyUSB0',9600)
ser = serial.Serial('/dev/ttyNANO',9600)
ser.flushInput()

# Setup the button
GPIO.setmode(GPIO.BOARD)
# 10 left 11 center 13 right
buttonPin1 = 13 # instavintage Rechts
buttonPin2 = 10 # 10x15 Links
buttonPin3 = 11 # 4 photos Mitte
buttonPin4 = 19 #photoswitch on/off
buttonPin5 = 26 #vintagemode on/off
buttonPin6 = 33 #watermark_mode on/off

GPIO.setup(buttonPin1, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(buttonPin2, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(buttonPin3, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(buttonPin4, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(buttonPin5, GPIO.IN, pull_up_down = GPIO.PUD_UP)
GPIO.setup(buttonPin6, GPIO.IN, pull_up_down = GPIO.PUD_UP)

#buttonPress = True
#switchStatus = True

#Kill gphoto2 process that starts whenever we connect the camera
def killgphoto2Process():
    p = subprocess.Popen(['ps', '-A'], stdout=subprocess.PIPE)
    out, err = p.communicate()
    
    # Search for the line that has the process we want to kill
    for line in out.splitlines():
            if b'gvfsd-gphoto2' in line:
                #kill the process!
                pid = int(line.split(None,1)[0])
                os.kill(pid, signal.SIGKILL)
                            
shot_date = datetime.now().strftime("%Y-%m-%d")
picID = "PiShots"

clearCommand    = ["--folder", "/store_00020001/DCIM/100CANON", "-R", "--delete-all-files"]
triggerCommand  = ["--trigger-capture"]
downloadCommand = ["--get-all-files"]
largeCommand    = ["--set-config-index", "/main/imgsettings/imageformat=0"]
mediumCommand   = ["--set-config-index", "/main/imgsettings/imageformat=2"]
smallCommand    = ["--set-config-index", "/main/imgsettings/imageformat=4"]

def createSaveFolder():
    try:
        os.makedirs(save_location)
    except:
        print("directory already exists...")
    os.chdir(save_location)

def captureImage():
    ret=gp(triggerCommand)
    ser.write(str.encode("p")) #Nano mit Animation
    #gp(triggerCommand)
    sleep(3)
    gp(downloadCommand)
    gp(clearCommand)

# rename the first JPG file and return the renamed filename
# jpg_file: if given additionally to copy the file to the vault rename 
#           the original image to jpg_file
#           if not given move the original file to the vault directory with a datetime-stamp
# vault: directory to store all original files
def renameFiles(jpg_file=None, vault=image_vault):
    for filename in os.listdir("."):
        if len(filename) > 10 and filename.endswith(".JPG"):
            shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            vault_file=os.path.join(vault, (shot_time + ".JPG"))
            if jpg_file:
                shutil.copy2(filename, vault_file)
                os.rename(filename, jpg_file)
                return jpg_file
            else:
                os.rename(filename, vault_file)
                return vault_file

def printFilesStiched():
    print("printFilesStiched")
    killgphoto2Process()
    gp(smallCommand) #new feature - quality of campic
    process=None
    for img_id, arduino_command in enumerate(["a", "b", "c", "d"]):
        jpg_file="{:d}.JPG".format(img_id+1)
        # trigger command
        killgphoto2Process()
        gp(clearCommand)
        ser.write(str.encode("e")) #Nano mit Animation
        createSaveFolder()
        ser.write(str.encode(arduino_command))	
        sleep(4)
        captureImage()
        renameFiles(jpg_file)
        # wait for previous picture to be resized
        if process:
            process.wait()
        # resize current picture
        process = subprocess.Popen(["convert", jpg_file, "-resize", "500x", jpg_file])

    # wait for last picture to be resized
    if process:
        process.wait()
    # stitch pictures
    if watermark_mode:
        commands=[
            # stack the four pictues one after another and rotate the result
            "convert 1.jpg 2.jpg 3.jpg 4.jpg " + text_vorlage_A + " -append -rotate 270 output.jpg", 
            # two image-rows
            "convert output.jpg output.jpg -append output.jpg"]
    else:
        commands=[
            # stack the four pictues one after another and rotate the result
            "convert 1.jpg 2.jpg 3.jpg 4.jpg " + text_vorlage_B + " -append -rotate 270 output.jpg", 
            # two image-rows
            "convert output.jpg output.jpg -append output.jpg"]
    for command in commands:
        print("running command: ", command)
        ret = subprocess.run(command.split(), 
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        print("stdout: ", ret.stdout.decode("utf-8"))
        print("stderr: ", ret.stderr.decode("utf-8"))
    
    shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    stitch_filename = os.path.join(image_vault2, ("Stitched_" + shot_time + ".JPG"))
    os.rename("output.jpg", stitch_filename)
    if printon == True:
        printPic2Cut(stitch_filename)

def printFilesNormal():
    # trigger command
    
    if not watermark_mode:
        print("printFilesNormal")
        photoCommand = mediumCommand #largeCommand
    else:
        print("printFilesNormalWatermark")
        photoCommand = mediumCommand
    killgphoto2Process()
    gp(photoCommand) #new feature - quality of campic
    createSaveFolder()
    ser.write(str.encode("s"))	
    sleep(2.5)
    captureImage()
    
    # move file to vault and return vault_filename
    vault_filename = renameFiles()
    file_to_print=vault_filename
    if watermark_mode: 
        # overlay the original image with the watermark A
        shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        watermark_filename = os.path.join(image_vault2, ("Watermark_" + shot_time + ".JPG"))
        file_to_print = watermark_filename
        process = subprocess.Popen([
            "convert", vault_filename,
            "-gravity", "south-east",
            watermark_vorlage_A,
            "-composite", watermark_filename])
        process.wait()
    else:
        # overlay the original image with the watermark B
        shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        watermark_filename = os.path.join(image_vault2, ("Watermark_" + shot_time + ".JPG"))
        file_to_print = watermark_filename
        process = subprocess.Popen([
            "convert", vault_filename,
            "-gravity", "south-east",
            watermark_vorlage_B,
            "-composite", watermark_filename])
        process.wait()
    if printon == True:
        printPic(file_to_print)

def printFilesInstaVintage():
    if vintagemode == True:
        # trigger command
        print("printFilesVintage")
        killgphoto2Process()
        gp(clearCommand)
        gp(mediumCommand) #new feature - quality of campic
        createSaveFolder()
        ser.write(str.encode("s"))	
        sleep(2.5)
        captureImage()
        # copy original image to vault
        vault_filename = renameFiles()
        # filename for stitched vintage image (will be printed)
        shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        instavintage_filename = os.path.join(image_vault2, ("InstaVintage_" + shot_time + ".JPG"))
        
        vintagename = get_vintagepic()
        # stitch pictures
        if watermark_mode:
            commands=[
                # scale down the raw image
                "convert " + vault_filename + " -resize x640 -crop 640x640+160+0 insta_temporary.jpg",
                # put the vintage image and the scaled down raw image in a new file
                "convert " + insta_vintage_vorlage +
                    " -gravity west " + vintagename + " -geometry +55-125 -composite" +
                    " -gravity east insta_temporary.jpg -geometry +55-125 -composite " +
                    " -gravity west " + watermark_background_vorlage_A + " -geometry +0-0 -composite " +
                    instavintage_filename]
        else:
            commands=[
                # scale down the raw image
                "convert " + vault_filename + " -resize x640 -crop 640x640+160+0 insta_temporary.jpg",
                # put the vintage image and the scaled down raw image in a new file
                "convert " + insta_vintage_vorlage +
                    " -gravity west " + vintagename + " -geometry +55-125 -composite" +
                    " -gravity east insta_temporary.jpg -geometry +55-125 -composite " +
                    " -gravity west " + watermark_background_vorlage_B + " -geometry +0-0 -composite " +
                    instavintage_filename]
        for command in commands:
            print("running command: ", command)
            ret = subprocess.run(command.split(), 
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            print("stdout: ", ret.stdout.decode("utf-8"))
            print("stderr: ", ret.stderr.decode("utf-8"))
        if printon == True:
            printPic(instavintage_filename)
    elif vintagemode == False:
        # trigger command
        print("printFilesInsta2Pics")
        killgphoto2Process()
        gp(mediumCommand) #new feature - quality of campic
        process=None
        for img_id, arduino_command in enumerate(["m", "n"]):
            jpg_file="{:d}.JPG".format(img_id+1)
            # trigger command
            killgphoto2Process()
            gp(clearCommand)
            ser.write(str.encode("e")) #Nano mit Animation
            createSaveFolder()
            ser.write(str.encode(arduino_command))	
            sleep(4)
            captureImage()
            renameFiles(jpg_file)
            # wait for previous picture to be resized
            if process:
                process.wait()
            # resize current picture
            process = subprocess.Popen([
                "convert", jpg_file,
                # resize the jpg file to be 640 pixels high (scale width accordingly)
                "-resize", "x640",
                # crop the image
                "-crop", "640x640+160+0", jpg_file])
        
        # stitch pictures
        if process:
            print("waiting 4 stitching...")
            process.wait()
        print("stitching...")
        shot_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        stitch_filename = os.path.join(image_vault2, ("Insta2Pics_" + shot_time + ".JPG"))
        if watermark_mode:
            commands=[
                "convert " + insta_vorlage_A +
                    " -gravity west 1.JPG -geometry +55-125 -composite " +
                    " -gravity east 2.JPG -geometry +55-125 -composite " +
                    " -gravity west " + watermark_background_vorlage_A + " -geometry +0-0 -composite " +
                    stitch_filename]
        else:
            commands=[
                "convert " + insta_vorlage_B +
                    " -gravity west 1.JPG -geometry +55-125 -composite " +
                    " -gravity east 2.JPG -geometry +55-125 -composite " +
                    " -gravity west " + watermark_background_vorlage_B + " -geometry +0-0 -composite " +
                    stitch_filename]
        
        print("stitching success!")
        for command in commands:
            print("running command: ", command)
            ret = subprocess.run(command.split(), 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            print("stdout: ", ret.stdout.decode("utf-8"))
            print("stderr: ", ret.stderr.decode("utf-8"))

        if printon == True:
            printPic(stitch_filename)

#print the image stiched
def printPic2Cut(fileName):
    #addPreviewOverlay(100,200,55,"printing...")
    conn = cups.Connection()
    printers = conn.getPrinters()
    default_printer = list(printers.keys())[0]
    cups.setUser('pi')
    conn.printFile (default_printer, fileName, "boothy", {'fit-to-page':'True'})
    print("Print job successfully created.")
	

#print the image normal
def printPic(fileName):
    #addPreviewOverlay(100,200,55,"printing...")
    conn = cups.Connection()
    printers = conn.getPrinters()
    default_printer = list(printers.keys())[0]
    cups.setUser('pi')
    conn.printFile (default_printer, fileName, "boothy", {
        'fit-to-page':'True',
        'media':'om_w288h432_105.13x162.63mm'})
    print("Print job successfully created.")

try:
    while True:
        #print("Come on man, press the button!")
        buttonPress1 = GPIO.input(buttonPin1)
        buttonPress2 = GPIO.input(buttonPin2)
        buttonPress3 = GPIO.input(buttonPin3)
        printon = GPIO.input(buttonPin4)
        vintagemode = GPIO.input(buttonPin5)
        watermark_mode = GPIO.input(buttonPin6)
        #watermark_mode = True
        if buttonPress1 == False:
            print("ButtonPress InstaVintage")
            #printFilesNormal()
            printFilesInstaVintage()
            sleep(2)
            ser.write(str.encode("e")) #NANO animation ende
        elif buttonPress2 == False:
            print("ButtonPress Normal")
            printFilesNormal()
            #printFilesInstaVintage()
            sleep(2)
            ser.write(str.encode("e")) #NANO animation ende
        elif buttonPress3 == False:
            print("ButtonPress Stitched")
            printFilesStiched()
            sleep(2)
            ser.write(str.encode("e")) #NANO animation ende
        sleep(0.1)
finally:
    # Reset the GPIO Pins to a safe state
    GPIO.cleanup()
